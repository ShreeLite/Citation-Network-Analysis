"""Step 6 — Automated QA -> qa/qa_report.md, data/processed/qa_summary.csv, review/audit_sample.csv"""
from __future__ import annotations

import json
import random

import pandas as pd

from common.config import DATA, PROCESSED, QA, REVIEW, cfg, collection_date, setup_logging
from common.dblp_parse import person_publications, prefetch
from common.sources import oa_get, short_id
from common.titles import normalise_title

log = setup_logging("06_qa")
Y0, Y1 = cfg()["years"]["start"], cfg()["years"]["end"]
SPEC_COLS = ["group", "institution", "author", "title", "year", "type", "journal_name", "issn", "doi", "citations",
             "quartile", "coauthor_institutes", "cites_indian_inst", "cited_by_indian_inst"]


def dblp_check(roster, src, ml) -> pd.DataFrame:
    """Recall of each person's DBLP journal/conference records (2016–2026) in our main set."""
    main_pairs = set(zip(ml.faculty_id, ml.paper_id))
    cl_paper = src.set_index("rid").cluster.to_dict()
    papers = pd.read_parquet(PROCESSED / "papers_enriched.parquet")[["cluster", "paper_id"]]
    cl_to_paper = dict(zip(papers.cluster, papers.paper_id))
    rows = []
    prefetch(roster[(roster.is_core == "True") & roster.dblp_pid.ne("")].dblp_pid.tolist())
    for f in roster[(roster.is_core == "True") & roster.dblp_pid.ne("")].itertuples():
        try:
            dp = person_publications(f.dblp_pid)
        except Exception:
            continue
        recs = [r for r in dp["records"] if r["year"] and Y0 <= r["year"] <= Y1 and r["dblp_type"] in ("journal", "conference")]
        found = sum(1 for r in recs if (f.faculty_id, cl_to_paper.get(cl_paper.get(f"dblp:{r['dblp_key']}"))) in main_pairs)
        ours = ml[ml.faculty_id == f.faculty_id].paper_id.nunique()
        rows.append({"faculty_id": f.faculty_id, "name": f.name, "institution": f.institution, "dblp_pid": f.dblp_pid,
                     "dblp_count": len(recs), "our_count": ours, "dblp_found_in_ours": found,
                     "dblp_recall": round(found / len(recs), 3) if recs else None,
                     "count_ratio_ours_over_dblp": round(ours / len(recs), 3) if recs else None})
    return pd.DataFrame(rows)


def cited_by_spot_check(mp, n=20) -> pd.DataFrame:
    insts = json.loads((PROCESSED / "institutions.json").read_text())
    cand = mp[mp.n_citing_indian_other > 0].dropna(subset=["openalex_id"])
    if cand.empty:
        return pd.DataFrame()
    rows = []
    for p in cand.sample(min(n, len(cand)), random_state=7).itertuples():
        res = oa_get("works", filter=f"cites:{p.openalex_id},authorships.institutions.country_code:IN", group_by="authorships.institutions.id")
        own = set().union(*(insts[i]["openalex_ids_all"] for i in p.our_institutions.split(";")))
        direct = {short_id(g["key"]) for g in res.get("group_by", []) if g.get("key") and short_id(g["key"]) not in own}
        ours = {s.rsplit(" (", 1)[0] for s in str(p.citing_indian_institutions).split("; ") if s}
        rows.append({"paper_id": p.openalex_id, "pipeline_n_institutions": len(ours), "group_by_n_institutions_incl_non_IN": len(direct),
                     "pipeline_flag": bool(p.cited_by_indian_inst)})
    return pd.DataFrame(rows)


def main() -> None:
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    mp = pd.read_parquet(PROCESSED / "main_papers.parquet")
    ml = pd.read_parquet(PROCESSED / "main_links.parquet")
    src = pd.read_parquet(PROCESSED / "source_records.parquet")
    merge = json.loads((PROCESSED / "merge_report.json").read_text())
    core = roster[roster.is_core == "True"]
    lines = [f"# QA report — Group 9 (IIIT-H + IIIT-D)", "", f"Collection date: {collection_date()}  ",
             f"Main set: {len(mp):,} papers, {len(ml):,} faculty–paper links, {ml.faculty_id.nunique()} of {len(core)} core faculty with ≥1 paper.", ""]
    summary = []

    # 1. DBLP spot check
    dc = dblp_check(roster, src, ml)
    if len(dc):
        pooled = dc.dblp_found_in_ours.sum() / max(1, dc.dblp_count.sum())
        lines += ["## 1. DBLP spot check", "",
                  f"Faculty with a DBLP PID: {len(dc)} of {len(core)} core. Pooled recall of DBLP journal+conference records "
                  f"(2016–2026) in our main set: **{pooled:.1%}**. Median per-person recall: {dc.dblp_recall.median():.1%}. "
                  f"Median ours/DBLP count ratio: {dc.count_ratio_ours_over_dblp.median():.2f} (>1 is expected: we also hold non-CS venues DBLP does not index).", "",
                  "Worst 20 by recall:", "", dc.sort_values(["dblp_recall", "dblp_count"], ascending=[True, False]).head(20)
                  [["name", "institution", "dblp_count", "our_count", "dblp_found_in_ours", "dblp_recall"]].to_markdown(index=False), ""]
        dc.to_csv(QA / "dblp_spot_check.csv", index=False)
        summary.append(("dblp_pooled_recall", round(pooled, 4)))

    # 2. Audit sample
    random.seed(9)
    audit = mp.sample(min(50, len(mp)), random_state=9)
    audit.assign(verified="", notes="").to_csv(REVIEW / "audit_sample.csv", index=False)
    lines += ["## 2. Random audit sample", "", "50 random papers with all fields: `review/audit_sample.csv` (fill `verified` = Y/N).", ""]

    # 3. Duplicates
    dup_doi = mp[mp.doi.notna() & mp.doi.duplicated(keep=False)]
    nt = mp.title.map(normalise_title)
    dup_title = mp[(nt + "|" + mp.year.astype(str)).duplicated(keep=False) & nt.ne("")]
    lines += ["## 3. Duplicate check", "", f"Papers sharing a DOI: {len(dup_doi)}. Papers with identical normalised title and year: {len(dup_title)}.", ""]
    if len(dup_title):
        dup_title[["paper_id", "doi", "title", "year", "type", "journal_name", "sources"]].to_csv(QA / "possible_duplicates.csv", index=False)
        lines += ["Listed in `qa/possible_duplicates.csv` (many are legitimate conference + journal versions with different DOIs).", ""]
    summary += [("dup_doi_rows", len(dup_doi)), ("dup_title_rows", len(dup_title))]

    # 4. Missing-field rates
    fields = {"doi": mp.doi.notna() & mp.doi.ne(""), "issn (journals)": mp[mp.type == "journal"].issn.ne(""),
              "quartile (journals)": mp[mp.type == "journal"].quartile.ne(""),
              "CORE rank (conferences)": mp[mp.type == "conference"].core_rank.ne(""),
              "journal_name": mp.journal_name.fillna("").ne(""), "citations": mp.citations.notna(),
              "coauthor_institutes": mp.coauthor_institutes.fillna("").ne(""), "field": mp.field.fillna("").ne(""),
              "citations_s2": mp.citations_s2.notna()}
    tab = pd.DataFrame([{"field": k, "filled": f"{v.mean():.1%}", "missing": f"{1 - v.mean():.1%}", "n": len(v)} for k, v in fields.items()])
    lines += ["## 4. Field coverage", "", tab.to_markdown(index=False), ""]
    summary += [(f"filled_{k}", round(v.mean(), 4)) for k, v in fields.items()]

    # 5. Faculty outliers
    per = ml.groupby("faculty_id").paper_id.nunique()
    zero = core[~core.faculty_id.isin(per.index)]
    hi = per[per > per.quantile(0.99)]
    lines += ["## 5. Faculty with zero or suspiciously many papers", "",
              f"Core faculty with zero main-set papers: {len(zero)}: " + ", ".join(f"{r.name} ({r.institution}, {r.unit or 'no unit'})" for r in zero.itertuples()), "",
              "Top 1% by paper count (check for over-merged profiles): " + ", ".join(f"{roster.set_index('faculty_id').at[f, 'name']} ({n})" for f, n in hi.items()), ""]
    summary += [("faculty_zero_papers", len(zero))]

    # 6. Year distribution
    yd = mp.groupby(["year", "type"]).size().unstack(fill_value=0)
    lines += ["## 6. Year distribution (2026 is partial)", "", yd.to_markdown(), ""]

    # 7. Merge and type evidence
    lines += ["## 7. Merge diagnostics", "", f"Source records: {merge['records_by_source']}. Fuzzy title threshold used: {merge['fuzzy_threshold_used']}.", "",
              pd.DataFrame(merge["fuzzy_tuning"]).to_markdown(index=False), "",
              f"Links filtered as over-merged OpenAlex profiles: {merge['overmerge_filtered']} (`review/overmerge_filtered.csv`). "
              f"Pre-joining links: {merge['links_pre_joining']}. After-leaving links: {merge['links_after_leaving']}.", ""]
    agree = mp[(mp.core_rank_portal.fillna("") != "") & mp.core_rank.ne("")]
    if len(agree):
        rate = (agree.core_rank_portal == agree.core_rank).mean()
        lines += [f"CORE rank agreement with the IIIT-H portal's own labels: {rate:.1%} of {len(agree)} papers where both exist.", ""]
        summary.append(("core_agreement_with_portal", round(rate, 4)))

    # 8. cited_by spot check
    cb = cited_by_spot_check(mp)
    if len(cb):
        lines += ["## 8. cited_by_indian_inst spot check (per-paper group_by vs batched pipeline)", "", cb.to_markdown(index=False), ""]

    # 9. Spec columns
    lines += ["## 9. Official file", "", f"`group9_data.csv` columns (asserted in order): {', '.join(SPEC_COLS)}.", ""]
    (QA / "qa_report.md").write_text("\n".join(lines))
    pd.DataFrame(summary, columns=["metric", "value"]).to_csv(PROCESSED / "qa_summary.csv", index=False)
    print("\n".join(lines[:12]))
    print(f"... full report: {QA/'qa_report.md'}")


if __name__ == "__main__":
    main()
