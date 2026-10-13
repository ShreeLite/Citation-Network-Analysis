"""Step 5 — Network files with the exact spec columns plus extras.

  data/processed/citation_network.csv
  data/processed/authorship_network.csv                 faculty-only (main analysis)
  data/processed/authorship_network_all_coauthors.csv   all co-authors (raw)
  data/processed/indian_connections.csv
  data/processed/citation_flow_by_year.csv
  data/processed/main_papers.parquet                    the analysis paper set (one row per paper)
  data/processed/main_links.parquet                     faculty-paper links of that set
"""
from __future__ import annotations

import gzip
import itertools
import json
from collections import Counter, defaultdict

import pandas as pd
from tqdm import tqdm

from common.config import DATA, EXTERNAL, PROCESSED, cfg, setup_logging
from common.sources import oa_get, short_id, slim_work

log = setup_logging("05_networks")
Y0, Y1 = cfg()["years"]["start"], cfg()["years"]["end"]
BIG = cfg()["flags"]["big_paper_authors"]
INCLUDE_PREPRINTS = cfg()["flags"]["include_preprints"]
TOPIC_PARTNERS = 100  # partners per institute for which topic sets are fetched (by shared papers + citations)


def main_set():
    papers = pd.read_parquet(PROCESSED / "papers_enriched.parquet")
    links = pd.read_parquet(PROCESSED / "faculty_paper_links.parquet")
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    core_ids = set(roster[(roster.is_core == "True")].faculty_id)
    keep_types = {"journal", "conference"} | ({"preprint"} if INCLUDE_PREPRINTS else set())
    ml = links[links.in_main_set & links.faculty_id.isin(core_ids)].copy()
    # one person with records at both institutes (moved, or adjunct at the other) must be credited
    # once per paper: the record whose institute is on the paper, else the one within tenure,
    # else the current one — otherwise they would 'co-author with themselves'
    status = roster.set_index("faculty_id").status.to_dict()
    ml["_person"] = ml.faculty_id.str.split(":", n=1).str[1]
    ml["_rank"] = (~ml.affiliated_on_paper.astype(bool)) * 4 + (~ml.within_tenure.astype(bool)) * 2 + ml.faculty_id.map(status).ne("current")
    before = len(ml)
    ml = ml.sort_values("_rank").drop_duplicates(["_person", "paper_id"]).drop(columns=["_person", "_rank"])
    log.info("credited %d duplicate same-person links to a single institute record", before - len(ml))
    mp = papers[papers.paper_id.isin(ml.paper_id) & papers.type.isin(keep_types) & papers.year.between(Y0, Y1)].copy()
    ml = ml[ml.paper_id.isin(mp.paper_id)].copy()
    mp["our_institutions"] = mp.paper_id.map(ml.groupby("paper_id").institution.apply(lambda s: ";".join(sorted(set(s)))))
    mp.to_parquet(PROCESSED / "main_papers.parquet", index=False)
    ml.to_parquet(PROCESSED / "main_links.parquet", index=False)
    log.info("main set: %d papers, %d faculty-paper links, %d faculty", len(mp), len(ml), ml.faculty_id.nunique())
    return papers, mp, ml, roster


def load_works(ids: set[str]) -> dict[str, dict]:
    works = {}
    with gzip.open(PROCESSED / "works_openalex.jsonl.gz", "rt") as fh:
        for line in fh:
            w = json.loads(line)
            wid = short_id(w["id"])
            if wid in ids:
                works[wid] = slim_work(w)
    return works


def citation_network(mp, works) -> pd.DataFrame:
    refs = pd.read_parquet(PROCESSED / "referenced_works.parquet").set_index("ref_id")
    ours = mp.dropna(subset=["openalex_id"]).set_index("openalex_id")
    rows = []
    for wid, p in ours.iterrows():
        src_doi = p.doi or wid
        for ref in (works.get(wid) or {}).get("referenced_works", []):
            t = short_id(ref)
            if t == wid:
                continue  # OpenAlex lists a few works as citing themselves: data error, dropped
            internal = t in ours.index
            if internal:
                tdoi, tinst = ours.at[t, "doi"] or t, ours.at[t, "our_institutions"]
            elif t in refs.index:
                tdoi, tinst = refs.at[t, "doi"] or t, refs.at[t, "inst_names"]
            else:
                tdoi, tinst = t, ""
            rows.append({"source_doi": src_doi, "target_doi": tdoi, "source_inst": p.our_institutions, "target_inst": tinst,
                         "year": int(p.year), "source_openalex_id": wid, "target_openalex_id": t, "internal_edge": internal})
    return pd.DataFrame(rows)


def authorship_networks(mp, ml, roster, works):
    name = roster.set_index("faculty_id").name.to_dict()
    inst = roster.set_index("faculty_id").institution.to_dict()
    rows, raw = [], []
    by_paper = ml.groupby("paper_id").faculty_id.apply(lambda s: sorted(set(s))).to_dict()
    for p in tqdm(mp.itertuples(), total=len(mp), desc="authorship edges"):
        facs = by_paper.get(p.paper_id, [])
        w = works.get(p.openalex_id) if p.openalex_id else None
        n_meta = int(p.n_authors) if pd.notna(p.n_authors) else 0
        n = len((w or {}).get("authorships", [])) or n_meta or len(facs)
        weight = 1 / max(1, n - 1)
        big = n > BIG
        doi = p.doi or p.paper_id
        for a, b in itertools.combinations(facs, 2):
            rows.append({"author_a": name[a], "author_b": name[b], "paper_doi": doi, "inst_a": inst[a], "inst_b": inst[b],
                         "year": int(p.year), "faculty_id_a": a, "faculty_id_b": b, "cross_institution": inst[a] != inst[b],
                         "n_authors": n, "weight": weight, "big_paper": big})
        # raw all-co-author version; for >BIG-author papers only pairs that involve a faculty member
        if w:
            aus = w.get("authorships", [])
            fac_aids = set()
            for f in facs:
                fac_aids |= FAC_AIDS.get(f, set())
            nodes = [(short_id(au["author"].get("id")), au["author"].get("display_name"),
                      "; ".join(i.get("display_name", "") for i in au.get("institutions", []))) for au in aus]
            for (ia, na, sa), (ib, nb, sb) in itertools.combinations(nodes, 2):
                if big and not ({ia, ib} & fac_aids):
                    continue
                raw.append({"author_a": na, "author_b": nb, "paper_doi": doi, "inst_a": sa, "inst_b": sb, "year": int(p.year),
                            "author_id_a": ia, "author_id_b": ib, "cross_institution": sa != sb, "n_authors": n,
                            "weight": weight, "big_paper": big})
    return pd.DataFrame(rows), pd.DataFrame(raw)


FAC_AIDS: dict[str, set[str]] = {}


def partner_topic_set(partner_id: str) -> set[str]:
    res = oa_get("works", filter=f"authorships.institutions.lineage:{partner_id},publication_year:{Y0}-{Y1}",
                 group_by="primary_topic.id")
    return {short_id(g["key"]) for g in res.get("group_by", []) if g.get("key") and g.get("count", 0) >= 2}


def indian_connections(mp, works, insts) -> tuple[pd.DataFrame, pd.DataFrame]:
    inst_ids = {i: set(v["openalex_ids_all"]) for i, v in insts.items()}
    pmap = pd.read_csv(EXTERNAL / "partner_type_map.csv", dtype=str).fillna("")
    ptype = dict(zip(pmap.institution, pmap.partner_type))
    shared, pid_of = defaultdict(Counter), {}
    for p in mp.itertuples():
        w = works.get(p.openalex_id) if p.openalex_id else None
        ours = p.our_institutions.split(";")
        seen = set()
        for au in (w or {}).get("authorships", []):
            for i in au.get("institutions", []):
                if i.get("country_code") != "IN":
                    continue
                iid = short_id(i["id"])
                lin = {short_id(x) for x in i.get("lineage", [])} | {iid}
                nm = i.get("display_name")
                pid_of[nm] = iid
                for o in ours:
                    if lin & inst_ids[o] or (o, nm) in seen:
                        continue
                    seen.add((o, nm))
                    shared[o][nm] += 1
    rec = pd.read_parquet(PROCESSED / "citations_received_by_partner.parquet")
    giv = pd.read_parquet(PROCESSED / "citations_given_to_partner.parquet")
    rows = []
    for o in insts:
        names = set(shared[o]) | set(rec[rec.our_inst == o].partner) | set(giv[giv.our_inst == o].partner)
        r_ = rec[rec.our_inst == o].set_index("partner").citations_received.to_dict()
        g_ = giv[giv.our_inst == o].set_index("partner").citations_given.to_dict()
        for nm in names:
            if nm == insts[o]["openalex_name"]:
                continue
            rows.append({"your_inst": o, "partner_inst": nm, "shared_papers": shared[o].get(nm, 0),
                         "total_citations": int(r_.get(nm, 0)), "citations_given_to_partner": int(g_.get(nm, 0)),
                         "partner_type": ptype.get(nm, "Other"), "partner_openalex_id": pid_of.get(nm, "")})
    ic = pd.DataFrame(rows)
    # partner ids for citation-only partners
    edges = pd.read_parquet(PROCESSED / "citing_indian_edges.parquet")
    pid_of.update(dict(zip(edges.partner, edges.partner_id)))
    ic["partner_openalex_id"] = ic.partner_inst.map(pid_of).fillna("")
    # topic Jaccard for the top partners (others left blank and documented)
    our_topics = {o: set(mp[mp.our_institutions.str.contains(o)].topic_id.dropna()) - {""} for o in insts}
    ic["rank_score"] = ic.shared_papers * 10 + ic.total_citations
    top = ic.sort_values("rank_score", ascending=False).groupby("your_inst").head(TOPIC_PARTNERS)
    jac = {}
    for pid in tqdm(top.partner_openalex_id.unique(), desc="partner topic sets"):
        if pid:
            jac[pid] = partner_topic_set(pid)
    ic["topic_jaccard"] = [
        round(len(our_topics[r.your_inst] & jac[r.partner_openalex_id]) / max(1, len(our_topics[r.your_inst] | jac[r.partner_openalex_id])), 4)
        if r.partner_openalex_id in jac else None for r in ic.itertuples()]
    ic = ic.drop(columns="rank_score").sort_values(["your_inst", "shared_papers", "total_citations"], ascending=[True, False, False])

    # year-wise flow: in-flow by citing year (from edges), out-flow by citing (our) paper year
    yr = mp.set_index("openalex_id").year.to_dict()
    oi = mp.set_index("openalex_id").our_institutions.to_dict()
    inflow = []
    for e in edges.itertuples():
        if e.cited_paper not in oi:
            continue
        lin = set(str(e.partner_lineage).split(";")) | {e.partner_id}
        for o in oi[e.cited_paper].split(";"):
            if not lin & inst_ids[o]:
                inflow.append({"your_inst": o, "year": e.citing_year, "direction": "in", "partner_inst": e.partner})
    refs = pd.read_parquet(PROCESSED / "referenced_works.parquet").set_index("ref_id")
    outflow = []
    for p in mp.dropna(subset=["openalex_id"]).itertuples():
        for ref in (works.get(p.openalex_id) or {}).get("referenced_works", []):
            t = short_id(ref)
            if t not in refs.index:
                continue
            r = refs.loc[t]
            names, ccs, ids_ = str(r.inst_names).split("; "), str(r.inst_ccs).split("; "), str(r.inst_ids).split(";")
            for nm, cc, iid in zip(names, ccs, ids_):
                if cc != "IN":
                    continue
                for o in p.our_institutions.split(";"):
                    if iid in inst_ids[o] or nm == insts[o]["openalex_name"]:
                        continue
                    outflow.append({"your_inst": o, "year": int(p.year), "direction": "out", "partner_inst": nm})
    flow = pd.DataFrame(inflow + outflow)
    fy = flow.groupby(["your_inst", "year", "direction"]).size().unstack("direction", fill_value=0).reset_index() if len(flow) else pd.DataFrame()
    if len(fy):
        fy = fy.rename(columns={"in": "citations_in_from_indian", "out": "citations_out_to_indian"})
        fy["impact_ratio_in_out"] = (fy.citations_in_from_indian / fy.citations_out_to_indian.replace(0, float("nan"))).round(3)
        fy["partial_year"] = fy.year.eq(cfg()["years"]["partial_year"])
    return ic, fy


def main() -> None:
    global FAC_AIDS
    papers, mp, ml, roster = main_set()
    insts = json.loads((PROCESSED / "institutions.json").read_text())
    ids = pd.read_csv(PROCESSED / "faculty_author_ids.csv", dtype=str)
    FAC_AIDS = ids.groupby("faculty_id").author_id.apply(set).to_dict()
    works = load_works(set(mp.openalex_id.dropna()))

    cn = citation_network(mp, works)
    cn.to_csv(PROCESSED / "citation_network.csv", index=False)
    an, raw = authorship_networks(mp, ml, roster, works)
    an.to_csv(PROCESSED / "authorship_network.csv", index=False)
    raw.to_csv(PROCESSED / "authorship_network_all_coauthors.csv", index=False)
    ic, fy = indian_connections(mp, works, insts)
    ic.to_csv(PROCESSED / "indian_connections.csv", index=False)
    fy.to_csv(PROCESSED / "citation_flow_by_year.csv", index=False)

    print("\n=== NETWORK FILES ===")
    print(f"citation edges: {len(cn):,} ({cn.internal_edge.sum():,} internal)")
    print(f"faculty co-authorship edges: {len(an):,} ({an.cross_institution.sum():,} cross-institution, {an.big_paper.sum():,} from >{BIG}-author papers)")
    print(f"all-co-author edges: {len(raw):,}")
    print(f"Indian partners: {ic.groupby('your_inst').size().to_dict()}")


if __name__ == "__main__":
    main()
