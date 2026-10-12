"""Step 2 — Author identity resolution: roster faculty -> all their OpenAlex author IDs.

Evidence, strongest first:
  1. ORCID (homepage or DBLP person record) -> OpenAlex authors with that ORCID
  2. DBLP DOI overlap: OpenAlex works for the person's DBLP DOIs; author IDs on those works
     whose name matches the faculty member (also finds split profiles outside the institute)
  3. Institution-affiliated candidate pool + fuzzy name match
  4. Topic/research-area overlap (only lowers confidence when clearly out of field)

Outputs
  data/processed/institutions.json
  data/processed/author_candidates.parquet      every scored (faculty, author) pair
  data/processed/faculty_author_ids.csv         accepted pairs (auto + your review decisions)
  review/author_matches_to_review.csv           pairs below auto-accept, with evidence
  review/possible_missing_faculty.csv           prolific institute authors not on the roster
`--reingest` re-reads your edited review file and rebuilds faculty_author_ids.csv only.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict

import pandas as pd
from tqdm import tqdm

from common.config import DATA, PROCESSED, REVIEW, cfg, setup_logging
from common.dblp_parse import person_publications
from common.names import name_similarity, normalise, surname_like, tokens
from common.sources import OA_MAX_OR, chunks, oa_get, oa_paginate, ror, short_id

log = setup_logging("02_identity")
Y0, Y1 = cfg()["years"]["start"], cfg()["years"]["end"]
AUTO = cfg()["thresholds"]["author_match_auto_accept"]
AUTHOR_SELECT = ("id,display_name,display_name_alternatives,orcid,works_count,cited_by_count,"
                 "summary_stats,affiliations,last_known_institutions,topics")


# ---------------------------------------------------------------------- institutions
def resolve_institutions() -> dict:
    p = PROCESSED / "institutions.json"
    out = {}
    for inst, meta in cfg()["institutes"].items():
        res = ror().get("https://api.ror.org/v2/organizations", params={"query": meta["ror_query"]})
        best = None
        for it in res.get("items", []):
            names = [n["value"] for n in it.get("names", [])]
            country = (it.get("locations") or [{}])[0].get("geonames_details", {}).get("country_code")
            doms = it.get("domains", [])
            if country == "IN" and any(d in doms for d in meta["email_domains"]):
                best = it
                break
            if country == "IN" and any(name_similarity(n, meta["full_name"]) > 0.9 for n in names) and best is None:
                best = it
        if not best:
            raise SystemExit(f"ROR: no confident match for {inst}")
        ror_id = best["id"]
        oa = oa_get("institutions", filter=f"ror:{ror_id}")
        if not oa.get("results"):
            raise SystemExit(f"OpenAlex has no institution for ROR {ror_id}")
        main = oa["results"][0]
        ids = {short_id(main["id"])}
        children = [a for a in main.get("associated_institutions", []) if a.get("relationship") == "child"]
        ids |= {short_id(c["id"]) for c in children}
        # also any OpenAlex institution whose lineage includes the main one
        lin = oa_get("institutions", filter=f"lineage:{short_id(main['id'])}", **{"per-page": 100})
        ids |= {short_id(r["id"]) for r in lin.get("results", [])}
        out[inst] = {
            "ror": ror_id,
            "ror_name": next((n["value"] for n in best["names"] if "ror_display" in n.get("types", [])), ""),
            "openalex_id": short_id(main["id"]),
            "openalex_name": main["display_name"],
            "openalex_ids_all": sorted(ids),
            "children": [{"id": short_id(c["id"]), "name": c["display_name"]} for c in children],
            "works_count": main.get("works_count"),
        }
        log.info("%s -> ROR %s, OpenAlex %s (%s), all ids %s", inst, ror_id, out[inst]["openalex_id"],
                 main["display_name"], out[inst]["openalex_ids_all"])
    p.write_text(json.dumps(out, indent=2))
    return out


# ---------------------------------------------------------------------- author pool
def institution_pool(inst_ids: list[str]) -> dict[str, dict]:
    pool = {}
    flt = "affiliations.institution.id:" + "|".join(inst_ids)
    for a in tqdm(oa_paginate("authors", flt, select=AUTHOR_SELECT), desc="author pool"):
        pool[short_id(a["id"])] = a
    return pool


def fetch_authors(ids: list[str]) -> dict[str, dict]:
    out = {}
    for ch in chunks(sorted(set(ids)), OA_MAX_OR):
        res = oa_get("authors", filter="ids.openalex:" + "|".join(ch), select=AUTHOR_SELECT, **{"per-page": 100})
        for a in res.get("results", []):
            out[short_id(a["id"])] = a
    return out


def authors_by_orcid(orcids: list[str]) -> dict[str, list[str]]:
    out = defaultdict(list)
    for ch in chunks(sorted(set(orcids)), OA_MAX_OR):
        res = oa_get("authors", filter="orcid:" + "|".join(ch), select="id,orcid", **{"per-page": 100})
        for a in res.get("results", []):
            o = (a.get("orcid") or "").rsplit("/", 1)[-1].upper()
            out[o].append(short_id(a["id"]))
    return out


def works_by_doi(dois: list[str]) -> list[dict]:
    out = []
    for ch in chunks(sorted(set(dois)), 50):  # DOI strings are long; keep URL size sane
        res = oa_get("works", filter="doi:" + "|".join(ch), select="id,doi,authorships", **{"per-page": 100})
        out += res.get("results", [])
    return out


# ---------------------------------------------------------------------- scoring
def author_names(a: dict) -> list[str]:
    return [a.get("display_name") or ""] + (a.get("display_name_alternatives") or [])


def best_name_sim(fac_names: list[str], a: dict) -> float:
    return max((name_similarity(f, n) for f in fac_names for n in author_names(a)), default=0.0)


def affiliated_years(a: dict, inst_ids: set[str]) -> list[int]:
    ys = []
    for af in a.get("affiliations") or []:
        if short_id(af["institution"]["id"]) in inst_ids:
            ys += af.get("years", [])
    return sorted(set(ys))


def topic_words(a: dict) -> set[str]:
    ws = set()
    for t in (a.get("topics") or [])[:15]:
        for k in ("display_name",):
            ws |= set(re.findall(r"[a-z]{4,}", t.get(k, "").lower()))
        for k in ("subfield", "field"):
            ws |= set(re.findall(r"[a-z]{4,}", (t.get(k) or {}).get("display_name", "").lower()))
    return ws


def area_words(r) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", f"{r.research_areas} {r.unit_text}".lower())) - {"research", "focuses", "centre", "center", "studies", "systems", "undertakes"}


def score(evid: dict) -> tuple[float, str]:
    """Combine evidence into (confidence, reason)."""
    ns = evid["name_sim"]
    if evid["orcid_match"]:
        return 0.99, "orcid"
    if evid["dblp_shared"] >= 3 and ns >= 0.6:
        return 0.97, "dblp_doi_overlap>=3"
    if evid["dblp_shared"] >= 1 and ns >= 0.75:
        return 0.88 if evid["inst_affiliated"] else 0.8, "dblp_doi_overlap"
    if ns >= 0.95 and evid["inst_affiliated"] and evid["affil_years_in_window"] >= 1:
        c = 0.86
        if evid["topic_overlap"] == 0 and evid["has_area_text"]:
            c = 0.7  # same name at institute but nothing in common topically: maybe a namesake
        if evid["n_roster_claims"] > 1:
            c = 0.6
        return c, "name+institution"
    if ns >= 0.85 and evid["inst_affiliated"]:
        return 0.65, "fuzzy_name+institution"
    if ns >= 0.85:
        return 0.4, "fuzzy_name_only"
    return 0.2, "weak"


def resolve(roster: pd.DataFrame, insts: dict) -> pd.DataFrame:
    all_inst_ids = {i: set(v["openalex_ids_all"]) for i, v in insts.items()}
    pools = {i: institution_pool(sorted(ids)) for i, ids in all_inst_ids.items()}
    log.info("author pools: %s", {i: len(p) for i, p in pools.items()})

    # surname index for fast candidate lookup
    index = defaultdict(set)
    for inst, pool in pools.items():
        for aid, a in pool.items():
            for n in author_names(a):
                for t in tokens(n):
                    if len(t) > 2:
                        index[t].add(aid)
    all_pool = {k: v for p in pools.values() for k, v in p.items()}

    # ORCIDs: roster + DBLP person records
    dblp_cache = {}
    for _, r in tqdm(roster.iterrows(), total=len(roster), desc="DBLP person records"):
        if r.dblp_pid:
            try:
                dblp_cache[r.faculty_id] = person_publications(r.dblp_pid)
            except Exception as e:
                log.warning("DBLP %s (%s): %s", r.dblp_pid, r["name"], e)
    orcid_of = {}
    for _, r in roster.iterrows():
        o = (r.orcid or "").upper()
        dp = dblp_cache.get(r.faculty_id)
        if not o and dp and dp["orcids"]:
            o = dp["orcids"][0].upper()
        if o:
            orcid_of[r.faculty_id] = o
    by_orcid = authors_by_orcid(list(orcid_of.values()))

    # DBLP DOI overlap -> author ids on those works
    dblp_hits: dict[str, Counter] = {}
    for fid, dp in tqdm(dblp_cache.items(), desc="DBLP DOI overlap"):
        dois = [d for rec in dp["records"] if rec["year"] and Y0 - 3 <= rec["year"] <= Y1 for d in rec["dois"]]
        if not dois:
            continue
        name = roster.set_index("faculty_id").at[fid, "name"]
        c = Counter()
        for w in works_by_doi(dois[:400]):
            for au in w.get("authorships", []):
                if name_similarity(name, au["author"].get("display_name") or "") >= 0.6 or \
                   name_similarity(dp["name"], au["author"].get("display_name") or "") >= 0.75:
                    c[short_id(au["author"]["id"])] += 1
        dblp_hits[fid] = c

    # candidate ids per faculty
    cand_ids: dict[str, set[str]] = {}
    for _, r in roster.iterrows():
        ids = set()
        for n in str(r.name_variants).split("; ") + [r["name"]]:
            for t in tokens(n):
                if len(t) > 2:
                    ids |= index.get(t, set())
        ids = {a for a in ids if best_name_sim([r["name"]], all_pool[a]) >= 0.75}
        ids |= set(by_orcid.get(orcid_of.get(r.faculty_id, ""), []))
        ids |= set(dblp_hits.get(r.faculty_id, {}).keys())
        cand_ids[r.faculty_id] = ids

    # fetch authors not in pool (ORCID/DBLP finds outside the institution)
    missing = {a for ids in cand_ids.values() for a in ids} - set(all_pool)
    all_pool.update(fetch_authors(list(missing)))

    claims = Counter(a for fid, ids in cand_ids.items() for a in ids
                     if best_name_sim([roster.set_index("faculty_id").at[fid, "name"]], all_pool.get(a, {})) >= 0.95)

    rows = []
    for _, r in roster.iterrows():
        aw = area_words(r)
        for aid in cand_ids[r.faculty_id]:
            a = all_pool.get(aid)
            if not a:
                continue
            yrs = affiliated_years(a, all_inst_ids[r.institution])
            ev = {
                "name_sim": round(best_name_sim([r["name"]] + str(r.name_variants).split("; "), a), 3),
                "orcid_match": bool(orcid_of.get(r.faculty_id)) and (a.get("orcid") or "").upper().endswith(orcid_of.get(r.faculty_id, "-")),
                "dblp_shared": dblp_hits.get(r.faculty_id, Counter()).get(aid, 0),
                "inst_affiliated": bool(yrs),
                "affil_years_in_window": sum(Y0 <= y <= Y1 for y in yrs),
                "topic_overlap": len(aw & topic_words(a)),
                "has_area_text": bool(aw),
                "n_roster_claims": claims.get(aid, 0),
            }
            conf, reason = score(ev)
            rows.append({
                "faculty_id": r.faculty_id, "institution": r.institution, "name": r["name"], "unit": r.unit,
                "designation_class": r.designation_class,
                "author_id": aid, "author_name": a.get("display_name"), "orcid": (a.get("orcid") or "").rsplit("/", 1)[-1],
                "works_count": a.get("works_count"), "cited_by_count": a.get("cited_by_count"),
                "h_index_lifetime": (a.get("summary_stats") or {}).get("h_index"),
                "affiliated_years": ",".join(map(str, yrs)),
                "last_known": "; ".join(i.get("display_name", "") for i in a.get("last_known_institutions") or []),
                "top_topics": "; ".join(t["display_name"] for t in (a.get("topics") or [])[:4]),
                **ev, "confidence": conf, "reason": reason,
            })
    cands = pd.DataFrame(rows)
    # a candidate with zero name similarity is noise unless ORCID/DBLP says otherwise
    cands = cands[(cands.name_sim >= 0.6) | cands.orcid_match | (cands.dblp_shared > 0)]
    cands.to_parquet(PROCESSED / "author_candidates.parquet", index=False)

    # prolific institute authors not claimed by anyone -> possible missing/former faculty
    claimed = set(cands[cands.confidence >= 0.6].author_id)
    miss = []
    for inst, pool in pools.items():
        for aid, a in pool.items():
            yrs = affiliated_years(a, all_inst_ids[inst])
            n_win = sum(Y0 <= y <= Y1 for y in yrs)
            if aid in claimed or n_win < 4:
                continue
            h = (a.get("summary_stats") or {}).get("h_index") or 0
            if a.get("works_count", 0) >= 30 and h >= 10:
                miss.append({"institution": inst, "author_id": aid, "author_name": a["display_name"],
                             "works_count": a["works_count"], "h_index": h, "affiliated_years": ",".join(map(str, yrs)),
                             "last_known": "; ".join(i.get("display_name", "") for i in a.get("last_known_institutions") or []),
                             "top_topics": "; ".join(t["display_name"] for t in (a.get("topics") or [])[:3]),
                             "action": "faculty? (core/former/student/postdoc/external) — add to roster if faculty"})
    pd.DataFrame(miss).sort_values(["institution", "h_index"], ascending=[True, False]).to_csv(
        REVIEW / "possible_missing_faculty.csv", index=False)
    return cands


def sample_titles(aid: str, inst_ids: set[str], n: int = 3) -> str:
    res = oa_get("works", filter=f"author.id:{aid},publication_year:{Y0}-{Y1}", select="title,publication_year",
                 sort="cited_by_count:desc", **{"per-page": n})
    return " || ".join(f"{w['publication_year']}: {w['title']}" for w in res.get("results", []))


def write_review(cands: pd.DataFrame, insts: dict) -> None:
    rev = cands[(cands.confidence < AUTO) & (cands.confidence >= 0.4)].copy()
    ids = {i: set(v["openalex_ids_all"]) for i, v in insts.items()}
    rev["sample_titles"] = [sample_titles(a, ids[i]) for a, i in tqdm(zip(rev.author_id, rev.institution), total=len(rev), desc="sample titles")]
    rev["accept"] = ""  # you fill: Y / N
    cols = ["accept", "faculty_id", "name", "institution", "unit", "author_id", "author_name", "confidence", "reason",
            "name_sim", "orcid_match", "dblp_shared", "affiliated_years", "works_count", "h_index_lifetime",
            "last_known", "top_topics", "sample_titles", "n_roster_claims"]
    rev.sort_values(["institution", "name", "confidence"], ascending=[True, True, False])[cols].to_csv(
        REVIEW / "author_matches_to_review.csv", index=False)


def finalise(cands: pd.DataFrame) -> pd.DataFrame:
    acc = cands[cands.confidence >= AUTO][["faculty_id", "author_id", "confidence", "reason"]].assign(decided_by="auto")
    rp = REVIEW / "author_matches_to_review.csv"
    if rp.exists():
        rev = pd.read_csv(rp, dtype=str).fillna("")
        yes = rev[rev.accept.str.strip().str.upper().isin(["Y", "YES"])]
        acc = pd.concat([acc, yes[["faculty_id", "author_id", "confidence", "reason"]].assign(decided_by="manual_review")])
        no = rev[rev.accept.str.strip().str.upper().isin(["N", "NO"])]
        acc = acc.merge(no[["faculty_id", "author_id"]], how="left", indicator=True)
        acc = acc[acc._merge == "left_only"].drop(columns="_merge")
    extra = REVIEW / "author_ids_manual_add.csv"  # optional: faculty_id,author_id you add by hand
    if extra.exists():
        acc = pd.concat([acc, pd.read_csv(extra, dtype=str).assign(confidence=1.0, reason="manual_add", decided_by="manual_add")])
    acc = acc.drop_duplicates(["faculty_id", "author_id"])
    acc.to_csv(PROCESSED / "faculty_author_ids.csv", index=False)
    return acc


def update_roster(roster: pd.DataFrame, acc: pd.DataFrame, cands: pd.DataFrame, insts: dict) -> pd.DataFrame:
    ids = acc.groupby("faculty_id").author_id.apply(lambda s: "; ".join(sorted(s)))
    roster["openalex_ids"] = roster.faculty_id.map(ids).fillna("")
    # joining-year fallback: first institute-affiliated year (after PhD year if known)
    inst_ids = {i: set(v["openalex_ids_all"]) for i, v in insts.items()}
    c = cands.merge(acc[["faculty_id", "author_id"]])
    for i, r in roster.iterrows():
        if pd.notna(r.joining_year) and str(r.joining_year) not in ("", "nan"):
            continue
        yrs = sorted({int(y) for s in c[c.faculty_id == r.faculty_id].affiliated_years for y in str(s).split(",") if y})
        phd = re.search(r"((?:19|20)\d{2})", str(r.phd or ""))
        if phd:
            yrs = [y for y in yrs if y >= int(phd.group(1))]
        if yrs:
            roster.at[i, "joining_year"] = yrs[0]
            roster.at[i, "joining_year_source"] = "inferred_first_affiliated_paper"
            roster.at[i, "joining_year_confidence"] = 0.5
    roster.to_csv(DATA / "faculty_roster.csv", index=False)
    return roster


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reingest", action="store_true")
    args = ap.parse_args()
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype={"dblp_pid": str, "orcid": str}).fillna({"orcid": "", "dblp_pid": "", "research_areas": "", "unit_text": "", "unit": "", "name_variants": ""})
    insts = json.loads((PROCESSED / "institutions.json").read_text()) if args.reingest else resolve_institutions()
    if args.reingest:
        cands = pd.read_parquet(PROCESSED / "author_candidates.parquet")
    else:
        cands = resolve(roster, insts)
        write_review(cands, insts)
    acc = finalise(cands)
    roster = update_roster(roster, acc, cands, insts)

    core = roster[roster.is_core.astype(str).eq("True") | roster.designation_class.eq("former_unverified")]
    print("\n=== IDENTITY SUMMARY ===")
    for inst, g in core.groupby("institution"):
        matched = g.openalex_ids.ne("")
        print(f"{inst}: {matched.sum()}/{len(g)} core/former matched ({matched.mean():.0%}); "
              f"IDs per matched person: {g[matched].openalex_ids.str.count(';').add(1).mean():.2f}")
        print("  zero IDs:", ", ".join(g[~matched].name.tolist()) or "none")
    print("accepted pairs by reason:", acc.reason.value_counts().to_dict())
    print(f"review rows: {len(pd.read_csv(REVIEW/'author_matches_to_review.csv')) if (REVIEW/'author_matches_to_review.csv').exists() else 0}")


if __name__ == "__main__":
    main()
