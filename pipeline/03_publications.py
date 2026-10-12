"""Step 3 — Publications 2016–2026 from OpenAlex + DBLP + IIIT-H portal (+ Crossref for
DOI discovery), merged and deduplicated.

Outputs (data/processed/)
  works_openalex.jsonl.gz     full OpenAlex work JSON for every candidate work
  source_records.parquet      one row per (source record) with its cluster id
  papers.parquet              one row per merged paper
  faculty_paper_links.parquet one row per (faculty, paper) with tenure/affiliation flags
  merge_report.json           counts, fuzzy-threshold tuning table
  review/overmerge_filtered.csv   faculty-paper links dropped as over-merged-profile suspects
"""
from __future__ import annotations

import gzip
import json
import re
from collections import Counter, defaultdict

import pandas as pd
from rapidfuzz import fuzz
from tqdm import tqdm

from common.config import DATA, PROCESSED, REVIEW, cfg, collection_date, setup_logging
from common.dblp_parse import person_publications
from common.dedup import cluster, tune_threshold
from common.iiith_portal import all_publications as portal_publications
from common.names import name_similarity
from common.sources import OA_MAX_OR, chunks, crossref, oa_get, oa_paginate, short_id
from common.titles import is_arxiv_doi, normalise_doi, normalise_title

log = setup_logging("03_publications")
Y0, Y1 = cfg()["years"]["start"], cfg()["years"]["end"]
THRESH = cfg()["thresholds"]["title_fuzzy"]


def load_inputs():
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    ids = pd.read_csv(PROCESSED / "faculty_author_ids.csv", dtype=str)
    insts = json.loads((PROCESSED / "institutions.json").read_text())
    return roster, ids, insts


# ------------------------------------------------------------------ OpenAlex
def openalex_works(author_ids: list[str], inst_ids: list[str]) -> dict[str, dict]:
    works: dict[str, dict] = {}
    for ch in tqdm(list(chunks(sorted(set(author_ids)), OA_MAX_OR)), desc="OpenAlex works by author"):
        flt = f"author.id:{'|'.join(ch)},publication_year:{Y0}-{Y1}"
        for w in oa_paginate("works", flt):
            works[short_id(w["id"])] = w
    # safety net: everything with an institute affiliation in the window
    flt = f"authorships.institutions.lineage:{'|'.join(inst_ids)},publication_year:{Y0}-{Y1}"
    n0 = len(works)
    inst_only = {}
    for w in tqdm(oa_paginate("works", flt), desc="OpenAlex works by institution"):
        wid = short_id(w["id"])
        if wid not in works:
            inst_only[wid] = w
    log.info("OpenAlex: %d works via author ids, %d extra institution-affiliated works", n0, len(inst_only))
    return works, inst_only


def oa_doi(w: dict) -> str | None:
    return normalise_doi(w.get("doi"))


def oa_is_preprint(w: dict) -> bool:
    if w.get("type") == "preprint" or is_arxiv_doi(oa_doi(w)):
        return True
    src = ((w.get("primary_location") or {}).get("source") or {})
    return src.get("type") == "repository" and not w.get("type") in ("article",) and "arxiv" in (src.get("display_name") or "").lower()


def works_by_dois(dois: list[str]) -> dict[str, dict]:
    out = {}
    for ch in chunks(sorted(set(dois)), 50):
        res = oa_get("works", filter="doi:" + "|".join(ch), **{"per-page": 100})
        for w in res.get("results", []):
            out[short_id(w["id"])] = w
    return out


# ------------------------------------------------------------------ Crossref DOI discovery
def crossref_find_doi(title: str, year: int | None, author: str) -> str | None:
    if not title or len(title) < 15:
        return None
    params = {"query.bibliographic": title, "rows": 3, "select": "DOI,title,issued,author"}
    if author:
        params["query.author"] = author
    try:
        res = crossref().get("https://api.crossref.org/works", params=params)
    except Exception as e:
        log.info("crossref search failed: %s", e)
        return None
    nt = normalise_title(title)
    for it in res.get("message", {}).get("items", []):
        t = (it.get("title") or [""])[0]
        y = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
        if fuzz.ratio(nt, normalise_title(t)) >= 95 and (not year or not y or abs(int(y) - year) <= 1):
            return normalise_doi(it["DOI"])
    return None


# ------------------------------------------------------------------ main
def main() -> None:
    roster, ids, insts = load_inputs()
    fac = roster.set_index("faculty_id")
    inst_of_fac = fac.institution.to_dict()
    inst_ids = {i: set(v["openalex_ids_all"]) for i, v in insts.items()}
    all_inst_ids = sorted(set().union(*inst_ids.values()))
    aid_to_fac = defaultdict(set)
    for r in ids.itertuples():
        aid_to_fac[r.author_id].add(r.faculty_id)

    works, inst_only = openalex_works(list(aid_to_fac), all_inst_ids)

    records: list[dict] = []
    # OpenAlex records
    for wid, w in works.items():
        facs = set()
        for au in w.get("authorships", []):
            facs |= aid_to_fac.get(short_id(au["author"].get("id")), set())
        records.append({"rid": f"oa:{wid}", "source": "openalex", "oa_id": wid, "doi": oa_doi(w),
                        "title": w.get("title") or w.get("display_name"), "year": w.get("publication_year"),
                        "is_preprint": oa_is_preprint(w), "faculty_ids": facs})

    # DBLP records
    dblp_recs = {}
    for f in tqdm(fac[fac.dblp_pid.ne("")].itertuples(), desc="DBLP"):
        try:
            dp = person_publications(f.dblp_pid)
        except Exception as e:
            log.warning("DBLP %s: %s", f.dblp_pid, e)
            continue
        for rec in dp["records"]:
            if not rec["year"] or not (Y0 <= rec["year"] <= Y1) or rec["dblp_type"] == "other":
                continue
            rid = f"dblp:{rec['dblp_key']}"
            if rid in dblp_recs:
                dblp_recs[rid]["faculty_ids"].add(f.Index)
                continue
            dblp_recs[rid] = {"rid": rid, "source": "dblp", "dblp_key": rec["dblp_key"],
                              "doi": next((d for d in rec["dois"] if not is_arxiv_doi(d)), rec["dois"][0] if rec["dois"] else None),
                              "title": rec["title"], "year": rec["year"], "is_preprint": rec["dblp_type"] == "preprint",
                              "faculty_ids": {f.Index}, "dblp_type": rec["dblp_type"], "dblp_venue": rec["venue"],
                              "dblp_venue_key": rec["venue_key"], "authors": rec["authors"]}
    records += list(dblp_recs.values())

    # IIIT-H portal records, linked to roster by author-name match
    iiith = fac[fac.institution.eq("IIIT-H")]
    portal = portal_publications()
    for k, p in enumerate(portal):
        if not p["year"] or not (Y0 <= p["year"] <= Y1):
            continue
        facs = set()
        for a in p["authors"]:
            for fid, nm in iiith.name.items():
                if name_similarity(a, nm) >= 0.9:
                    facs.add(fid)
        if not facs:
            continue
        records.append({"rid": f"portal:{k}", "source": "iiith_portal", "doi": p["doi"], "title": p["title"],
                        "year": p["year"], "is_preprint": False, "faculty_ids": facs,
                        "portal_type": p["portal_type"], "portal_venue": p["venue"], "portal_acronym": p["acronym"],
                        "core_rank_portal": p["core_rank_portal"], "authors": p["authors"]})

    # Records without an OpenAlex counterpart: find one by DOI (cheap) or Crossref title -> DOI
    oa_dois = {r["doi"] for r in records if r["source"] == "openalex" and r["doi"]}
    need = [r for r in records if r["source"] != "openalex"]
    for r in tqdm([r for r in need if not r["doi"]], desc="Crossref DOI discovery"):
        first_fac = next(iter(r["faculty_ids"]))
        surname = fac.at[first_fac, "name"].split()[-1]
        d = crossref_find_doi(r["title"], r["year"], surname)
        if d:
            r["doi"], r["doi_from"] = d, "crossref_title_search"
    missing_dois = sorted({r["doi"] for r in need if r["doi"] and r["doi"] not in oa_dois and not is_arxiv_doi(r["doi"])})
    extra = works_by_dois(missing_dois)
    log.info("found %d extra OpenAlex works by DOI for DBLP/portal-only records", len(extra))
    for wid, w in extra.items():
        if wid in works:
            continue
        works[wid] = w
        facs = set()
        d = oa_doi(w)
        for r in need:
            if r["doi"] == d:
                facs |= r["faculty_ids"]
        records.append({"rid": f"oa:{wid}", "source": "openalex", "oa_id": wid, "doi": d,
                        "title": w.get("title"), "year": w.get("publication_year"),
                        "is_preprint": oa_is_preprint(w), "faculty_ids": facs, "oa_found_via": "doi_from_other_source"})

    # cluster
    tuning = tune_threshold(records)
    cl = cluster(records, threshold=THRESH)
    for r in records:
        r["cluster"] = cl[r["rid"]]

    # persist full OpenAlex JSON (raw), for enrichment
    with gzip.open(PROCESSED / "works_openalex.jsonl.gz", "wt") as fh:
        for wid, w in works.items():
            fh.write(json.dumps(w) + "\n")

    papers, links, overmerge = build_tables(records, works, fac, inst_ids, aid_to_fac)
    srcdf = pd.DataFrame([{k: (";".join(sorted(v)) if isinstance(v, set) else v) for k, v in r.items()
                           if k not in ("_nt", "authors")} for r in records])
    srcdf.to_parquet(PROCESSED / "source_records.parquet", index=False)
    papers.to_parquet(PROCESSED / "papers.parquet", index=False)
    links.to_parquet(PROCESSED / "faculty_paper_links.parquet", index=False)
    pd.DataFrame(overmerge).to_csv(REVIEW / "overmerge_filtered.csv", index=False)

    # institution-only works whose authors look like roster faculty -> possibly missed author IDs
    miss = []
    for wid, w in inst_only.items():
        for au in w.get("authorships", []):
            nm = au["author"].get("display_name") or ""
            for fid, fn in fac.name.items():
                if fac.at[fid, "is_core"] == "True" and name_similarity(nm, fn) >= 0.95 and \
                        short_id(au["author"]["id"]) not in set(ids[ids.faculty_id == fid].author_id):
                    miss.append({"faculty_id": fid, "name": fn, "author_id": short_id(au["author"]["id"]),
                                 "author_name": nm, "work": wid, "title": w.get("title"), "year": w.get("publication_year")})
    mdf = pd.DataFrame(miss)
    if len(mdf):
        mdf = mdf.groupby(["faculty_id", "name", "author_id", "author_name"]).agg(
            n_works=("work", "nunique"), example=("title", "first")).reset_index().sort_values("n_works", ascending=False)
    mdf.to_csv(REVIEW / "possibly_missed_author_ids.csv", index=False)

    report = {
        "collected_at": collection_date(),
        "records_by_source": Counter(r["source"] for r in records),
        "papers": int(len(papers)),
        "papers_by_type_hint": papers.is_preprint_only.value_counts().to_dict(),
        "links": int(len(links)),
        "links_main": int(links.in_main_set.sum()),
        "links_pre_joining": int((links.status == "pre_joining").sum()),
        "links_after_leaving": int((links.status == "after_leaving").sum()),
        "overmerge_filtered": len(overmerge),
        "fuzzy_threshold_used": THRESH,
        "fuzzy_tuning": tuning,
        "possibly_missed_author_ids": int(len(mdf)),
    }
    (PROCESSED / "merge_report.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: v for k, v in report.items() if k != "fuzzy_tuning"}, indent=2, default=str))
    print("fuzzy tuning:", pd.DataFrame(tuning).to_string(index=False))


def faculty_field_profile(links_oa: list[tuple[str, dict]]) -> dict[str, Counter]:
    prof = defaultdict(Counter)
    for fid, w in links_oa:
        f = ((w.get("primary_topic") or {}).get("field") or {}).get("display_name")
        if f:
            prof[fid][f] += 1
    return prof


def build_tables(records, works, fac, inst_ids, aid_to_fac):
    by_cluster = defaultdict(list)
    for r in records:
        by_cluster[r["cluster"]].append(r)

    # pass 1: per-faculty field profile from *trusted* links (institute-affiliated authorship
    # or confirmed by DBLP/portal) — used to detect over-merged OpenAlex profiles
    trusted = []
    for cid, rs in by_cluster.items():
        srcs = {r["source"] for r in rs}
        for r in rs:
            if r["source"] != "openalex":
                continue
            w = works[r["oa_id"]]
            for au in w.get("authorships", []):
                for fid in aid_to_fac.get(short_id(au["author"].get("id")), ()):
                    affiliated = any(short_id(i["id"]) in inst_ids[fac.at[fid, "institution"]] for i in au.get("institutions", []))
                    if affiliated or srcs - {"openalex"}:
                        trusted.append((fid, w))
    profile = faculty_field_profile(trusted)

    papers, links, overmerge = [], [], []
    for cid, rs in by_cluster.items():
        oa = [r for r in rs if r["source"] == "openalex"]
        non_pre_oa = [r for r in oa if not r["is_preprint"]]
        primary = (non_pre_oa or oa or [None])[0]
        w = works.get(primary["oa_id"]) if primary else None
        all_pre = all(r["is_preprint"] for r in rs)
        srcs = sorted({r["source"] for r in rs})
        any_r = primary or next((r for r in rs if not r["is_preprint"]), rs[0])
        doi = (primary or {}).get("doi") or next((r["doi"] for r in rs if r["doi"] and not is_arxiv_doi(r["doi"])), None) \
            or next((r["doi"] for r in rs if r["doi"]), None)
        arxiv = sorted({r["doi"] for r in rs if r["doi"] and is_arxiv_doi(r["doi"])})
        dblp = next((r for r in rs if r["source"] == "dblp"), {})
        portal = next((r for r in rs if r["source"] == "iiith_portal"), {})
        paper_id = primary["oa_id"] if primary else (f"doi:{doi}" if doi else rs[0]["rid"])
        papers.append({
            "paper_id": paper_id,
            "cluster": cid,
            "openalex_id": primary["oa_id"] if primary else None,
            "openalex_ids_merged": ";".join(sorted({r["oa_id"] for r in oa})),
            "doi": doi,
            "arxiv_dois": ";".join(arxiv),
            "title": (w or {}).get("title") or any_r["title"],
            "year": (w or {}).get("publication_year") or any_r["year"],
            "is_preprint_only": all_pre,
            "sources": ";".join(srcs),
            "n_source_records": len(rs),
            "dblp_key": dblp.get("dblp_key"),
            "dblp_type": dblp.get("dblp_type"),
            "dblp_venue": dblp.get("dblp_venue"),
            "dblp_venue_key": dblp.get("dblp_venue_key"),
            "portal_type": portal.get("portal_type"),
            "portal_venue": portal.get("portal_venue"),
            "portal_acronym": portal.get("portal_acronym"),
            "core_rank_portal": portal.get("core_rank_portal"),
            "doi_from": next((r.get("doi_from") for r in rs if r.get("doi_from")), None),
        })
        # faculty links
        fac_src = defaultdict(set)
        for r in rs:
            for fid in r["faculty_ids"]:
                fac_src[fid].add(r["source"])
        for fid, s in fac_src.items():
            inst = fac.at[fid, "institution"]
            au_match = None
            if w:
                for au in w.get("authorships", []):
                    if fid in aid_to_fac.get(short_id(au["author"].get("id")), ()):
                        au_match = au
                        break
            affiliated = bool(au_match) and any(short_id(i["id"]) in inst_ids[inst] for i in au_match.get("institutions", []))
            if not affiliated and "iiith_portal" in s:
                affiliated = True  # institute-reported publication
            year = papers[-1]["year"]
            jy = pd.to_numeric(fac.at[fid, "joining_year"], errors="coerce")
            within = bool(pd.notna(jy) and year and year >= jy)
            leave = pd.to_numeric(fac.at[fid, "leaving_year"], errors="coerce") if "leaving_year" in fac else float("nan")
            after_leaving = bool(pd.notna(leave) and year and year > leave + 1 and not affiliated)

            # over-merge check: OpenAlex-only link, not affiliated, field alien to the person,
            # or raw author string unlike the person's name
            suspect = False
            if s == {"openalex"} and not affiliated and au_match:
                f = (((w or {}).get("primary_topic") or {}).get("field") or {}).get("display_name")
                prof = profile.get(fid, Counter())
                share = prof.get(f, 0) / max(1, sum(prof.values()))
                raw = au_match.get("raw_author_name") or ""
                if (f and sum(prof.values()) >= 5 and share < 0.05) or (raw and name_similarity(raw, fac.at[fid, "name"]) < 0.5):
                    suspect = True
                    overmerge.append({"faculty_id": fid, "name": fac.at[fid, "name"], "paper_id": paper_id,
                                      "title": papers[-1]["title"], "year": year, "field": f,
                                      "field_share_in_profile": round(share, 3), "raw_author_name": raw,
                                      "author_id": short_id(au_match["author"]["id"])})
            if suspect:
                status = "overmerge_filtered"
            elif after_leaving:
                status = "after_leaving"
            elif affiliated or within or pd.isna(jy):
                status = "main"
            else:
                status = "pre_joining"
            links.append({
                "faculty_id": fid, "paper_id": paper_id, "institution": inst,
                "link_sources": ";".join(sorted(s)),
                "author_position": (au_match or {}).get("author_position"),
                "affiliated_on_paper": affiliated,
                "within_tenure": within,
                "joining_year_unknown": bool(pd.isna(jy)),
                "status": status,
                "in_main_set": status == "main",
                "author_institutions_on_paper": "; ".join(i.get("display_name", "") for i in (au_match or {}).get("institutions", [])),
            })
    return pd.DataFrame(papers), pd.DataFrame(links), overmerge


if __name__ == "__main__":
    main()
