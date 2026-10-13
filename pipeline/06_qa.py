"""Step 6 — Automated QA -> qa/qa_report.md, data/processed/qa_summary.csv, review/audit_sample.csv"""
from __future__ import annotations

import json
import random

import pandas as pd

from common.config import DATA, DELIVERABLES, PROCESSED, QA, REVIEW, cfg, collection_date, setup_logging
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


def publisher_audit(sample: pd.DataFrame) -> pd.DataFrame:
    """Compare title / year / venue / type with the publisher's own record (Crossref) for papers
    that have a DOI. A mismatch is counted when the title similarity < 90, the year differs by
    more than 1, or the type disagrees (journal-article vs proceedings-article)."""
    from rapidfuzz import fuzz
    from common.sources import crossref
    rows = []
    for p in sample.itertuples():
        if not p.doi or str(p.doi).startswith("10.48550"):
            rows.append({"paper_id": p.paper_id, "checked": False, "reason": "no publisher DOI"})
            continue
        try:
            m = crossref().get(f"https://api.crossref.org/works/{p.doi}").get("message", {})
        except Exception as e:
            rows.append({"paper_id": p.paper_id, "checked": False, "reason": f"crossref: {e}"[:80]})
            continue
        t = (m.get("title") or [""])[0]
        y = ((m.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        ct = m.get("type", "")
        title_ok = fuzz.token_sort_ratio(normalise_title(t), normalise_title(p.title)) >= 90
        year_ok = y is None or abs(int(y) - int(p.year)) <= 1
        # Crossref registers some proceedings (AAAI, IJCAI, PMLR...) as journal-article; DBLP's
        # record type is authoritative for CS venues, so a DBLP-backed type is not a mismatch
        dblp_backed = isinstance(p.dblp_type, str) and p.dblp_type == p.type
        type_ok = dblp_backed or not ((ct == "journal-article" and p.type == "conference") or (ct == "proceedings-article" and p.type == "journal"))
        rows.append({"paper_id": p.paper_id, "doi": p.doi, "checked": True, "title_ok": title_ok, "year_ok": year_ok, "type_ok": type_ok,
                     "ok": title_ok and year_ok and type_ok, "publisher_title": t, "publisher_year": y, "publisher_type": ct,
                     "our_title": p.title, "our_year": p.year, "our_type": p.type})
    return pd.DataFrame(rows)


def checkpoint3(mp, ml, roster, summary) -> list[str]:
    L = []
    name = roster.set_index("faculty_id").name.to_dict()
    # counts and trends
    py = mp[mp.year < 2026].groupby("year").size()
    dips = [int(y) for y in py.index[1:-1] if py[y] < 0.7 * (py[y - 1] + py[y + 1]) / 2] if len(py) > 2 else []
    L += ["## 9. Papers per year (smoothness)", "", f"- Years dipping below 70% of their neighbours' mean: {dips or 'none'} (2026 excluded: partial).", ""]
    lk = ml.merge(mp[["paper_id", "year"]], on="paper_id")
    per = lk.groupby(["faculty_id", "year"]).paper_id.nunique().reset_index(name="n")
    top = per.sort_values("n", ascending=False).drop_duplicates("faculty_id").head(5)
    L += ["## 10. Most prolific faculty (max papers in one year)", "", "| Faculty | Year | Papers that year | Total 2016–26 |", "|---|---|---|---|"]
    for t in top.itertuples():
        tot = lk[lk.faculty_id == t.faculty_id].paper_id.nunique()
        L.append(f"| {name.get(t.faculty_id)} | {t.year} | {t.n}{' ⚠ > 40' if t.n > 40 else ''} | {tot} |")
    L.append("")
    tshare = mp.type.value_counts(normalize=True)
    L += ["## 11. Journal vs conference", "", f"- conference {tshare.get('conference', 0):.1%}, journal {tshare.get('journal', 0):.1%} "
          f"({'OK: conference-heavy as expected for CS institutes' if tshare.get('conference', 0) >= 0.4 else 'CHECK: journals dominate — DBLP merge may have failed'}).",
          "- Per institute: " + "; ".join(f"{i}: conf {g.type.eq('conference').mean():.0%}" for i, g in mp.assign(inst=mp.our_institutions.str.split(";")).explode("inst").groupby("inst")), ""]
    # arXiv beside published
    allp = pd.read_parquet(PROCESSED / "papers_enriched.parquet")
    pre = allp[allp.type.eq("preprint")]
    beside = set(pre.title.map(normalise_title)) & set(mp.title.map(normalise_title))
    L += ["## 12. Duplicates incl. arXiv beside published", "",
          f"- arXiv-only records whose title equals a published main-set paper: {len(beside)} (arXiv version > 2 years before publication). "
          "They are treated as the published paper: excluded from the preprint toggle, the preprints sheet and every count, so no paper appears twice.", ""]
    summary.append(("arxiv_beside_published", len(beside)))
    # ranking coverage + top venues
    j, c = mp[mp.type == "journal"], mp[mp.type == "conference"]
    prox = j.quartile_proxy_openalex.fillna("").ne("").mean() if "quartile_proxy_openalex" in j else 0.0
    L += ["## 13. Ranking coverage and top venues", "",
          f"- Journal papers with a Scimago SJR quartile: {j.quartile.fillna('').ne('').mean():.1%}"
          + ("" if j.quartile.fillna("").ne("").any() else " (Scimago files not available — Cloudflare blocks automated download)")
          + f"; with the labelled OpenAlex proxy quartile: {prox:.1%}.",
          f"- Conference papers with a CORE rank: {c.core_rank.fillna('').ne('').mean():.1%}.", ""]
    summary += [("filled_quartile_proxy (journals)", round(prox, 4))]
    for inst, g in mp.assign(inst=mp.our_institutions.str.split(";")).explode("inst").groupby("inst"):
        v = g.acronym.where(g.acronym.fillna("").ne(""), g.journal_name).value_counts().head(20)
        L += [f"**{inst} top 20 venues:** " + ", ".join(f"{k} ({n})" for k, n in v.items()), ""]
    # top cited
    L += ["## 14. Ten most-cited papers", "", "| Title | Venue | Year | Citations |", "|---|---|---|---|"]
    for p in mp.sort_values("citations", ascending=False).head(10).itertuples():
        L.append(f"| {str(p.title)[:90]} | {p.acronym or p.journal_name} | {p.year} | {int(p.citations or 0)} |")
    L += ["", "OpenAlex counts run below Google Scholar's; that is expected.", ""]
    # Indian flags
    a_, b_ = mp.cites_indian_inst.mean(), mp.cited_by_indian_inst.mean()
    L += ["## 15. Indian-citation flags", "", f"- cites_indian_inst TRUE: {a_:.1%}; cited_by_indian_inst TRUE: {b_:.1%} "
          f"({'OK: strictly between 0% and 100%' if 0 < a_ < 1 and 0 < b_ < 1 else 'BROKEN'}).", ""]
    edges = pd.read_parquet(PROCESSED / "citing_indian_edges.parquet")
    insts = json.loads((PROCESSED / "institutions.json").read_text())
    hand = []
    own_only = []
    for p in mp.dropna(subset=["openalex_id"]).itertuples():
        e = edges[edges.cited_paper == p.openalex_id]
        if len(e) and not p.cited_by_indian_inst:
            own_only.append(p)
        if len(own_only) >= 1:
            break
    sample = mp[mp.cited_by_indian_inst & mp.openalex_id.notna()].sample(min(4, int(mp.cited_by_indian_inst.sum())), random_state=3)
    for p in list(sample.itertuples()) + own_only[:1]:
        res = oa_get("works", filter=f"cites:{p.openalex_id},authorships.institutions.country_code:IN", group_by="authorships.institutions.id")
        own = set().union(*(insts[i]["openalex_ids_all"] for i in p.our_institutions.split(";")))
        ext = [g for g in res.get("group_by", []) if g.get("key") and short_id(g["key"]) not in own]
        # group_by spans all institutions of Indian-co-authored citing works; restrict to IN ones via names
        hand.append({"paper": p.openalex_id, "title": str(p.title)[:60], "flag": bool(p.cited_by_indian_inst),
                     "own_only_case": p in own_only, "citing_groups_excl_own": len(ext)})
    L += ["Hand-check (direct per-paper OpenAlex query):", "", pd.DataFrame(hand).to_markdown(index=False) if hand else "n/a", "",
          "A paper cited by Indian works only from its own institute must be FALSE — the own-only case above is FALSE when its row shows flag = False.", ""]
    # network files
    cn = pd.read_csv(PROCESSED / "citation_network.csv")
    an = pd.read_csv(PROCESSED / "authorship_network.csv")
    ic = pd.read_csv(PROCESSED / "indian_connections.csv")
    src_ok = cn.source_openalex_id.isin(mp.openalex_id).mean()
    self_c = int((cn.source_openalex_id == cn.target_openalex_id).sum())
    self_a = int((an.faculty_id_a == an.faculty_id_b).sum())
    self_a += int((an.faculty_id_a.str.split(":").str[1] == an.faculty_id_b.str.split(":").str[1]).sum())  # same person, two institute records
    pair = an.apply(lambda r: (min(r.faculty_id_a, r.faculty_id_b), max(r.faculty_id_a, r.faculty_id_b), r.paper_doi), axis=1)
    dup_ab = int(pair.duplicated().sum())
    own_partner = int(ic.apply(lambda r: r.partner_inst == insts[r.your_inst]["openalex_name"], axis=1).sum())
    L += ["## 16. Network files", "", f"- Citation edges whose source paper is in the papers table: {src_ok:.1%}", f"- Self-loops: citation {self_c}, authorship {self_a}",
          f"- A–B and B–A duplicates (same paper) in authorship edges: {dup_ab}", f"- Partner rows where an institute is its own partner: {own_partner}", ""]
    summary += [("citation_sources_in_papers", round(src_ok, 4)), ("self_loops", self_c + self_a), ("ab_ba_duplicates", dup_ab), ("own_partner_rows", own_partner)]
    # official file format
    off = DELIVERABLES / "group9_data.csv"
    if off.exists():
        o = pd.read_csv(off, encoding="utf-8-sig")
        nonascii = int(o.author.str.contains(r"[^\x00-\x7f]", regex=True).sum() + o.title.str.contains(r"[^\x00-\x7f]", regex=True).sum())
        L += ["## 17. Official file format", "", f"- Columns exactly as spec, in order: {list(o.columns) == SPEC_COLS}", f"- group = 9 on every row: {bool((o.group == 9).all())}",
              f"- Rows: {len(o):,}; written as UTF-8 with BOM so Excel shows accented/Indic characters correctly ({nonascii} cells contain non-ASCII text).",
              "- Files: " + ", ".join(f"{f} {'✓' if (DELIVERABLES / f).exists() else '✗'}" for f in ("group9_data.csv", "citation_network.csv", "authorship_network.csv", "indian_connections.csv")), ""]
    # publisher audit
    aud = publisher_audit(mp.sample(min(50, len(mp)), random_state=9))
    chk = aud[aud.checked.astype(bool)].copy()
    for c in ("title_ok", "year_ok", "type_ok", "ok"):
        chk[c] = chk[c].astype(bool)
    err = 1 - chk.ok.mean() if len(chk) else float("nan")
    aud.to_csv(QA / "audit_publisher_check.csv", index=False)
    L += ["## 18. Audit sample vs publisher record (Crossref)", "", f"- 50 random papers; {len(chk)} have a publisher DOI and were checked. Error rate: {err:.1%} "
          f"({'solid (< 5%)' if err < 0.05 else 'acceptable (5–10%)' if err < 0.10 else 'INVESTIGATE (> 10%)'}).",
          f"- Title mismatches {int((~chk.title_ok).sum())}, year mismatches {int((~chk.year_ok).sum())}, type mismatches {int((~chk.type_ok).sum())} — details in `qa/audit_publisher_check.csv`.", ""]
    summary.append(("audit_error_rate", round(err, 4)))
    return L


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
    dup_doi = mp[mp.doi.fillna("").ne("") & mp.doi.duplicated(keep=False)]
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

    # 9-17: checkpoint 3 checklist (qa/sanity_checklist.md)
    lines += checkpoint3(mp, ml, roster, summary)
    (QA / "qa_report.md").write_text("\n".join(lines))
    pd.DataFrame(summary, columns=["metric", "value"]).to_csv(PROCESSED / "qa_summary.csv", index=False)
    print("\n".join(lines[:12]))
    print(f"... full report: {QA/'qa_report.md'}")


if __name__ == "__main__":
    main()
