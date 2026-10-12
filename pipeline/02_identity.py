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
from common.dblp_parse import person_publications, prefetch
from common.names import name_similarity, normalise, surname_like, tokens
from common.sources import oa_get, oa_lookup, oa_paginate, ror, short_id

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


def institution_dois(insts: dict) -> dict[str, set[str]]:
    """DOIs of every 2016–2026 work OpenAlex affiliates with each institute (cached pages)."""
    from common.titles import normalise_doi
    out = {}
    for inst, v in insts.items():
        flt = f"authorships.institutions.lineage:{'|'.join(v['openalex_ids_all'])},publication_year:{Y0}-{Y1}"
        out[inst] = {normalise_doi(w.get("doi")) for w in oa_paginate("works", flt) if w.get("doi")}
    return out


# ---------------------------------------------------------------------- author pool
def institution_pool(inst_ids: list[str]) -> dict[str, dict]:
    pool = {}
    flt = "affiliations.institution.id:" + "|".join(inst_ids)
    for a in tqdm(oa_paginate("authors", flt, select=AUTHOR_SELECT), desc="author pool"):
        pool[short_id(a["id"])] = a
    return pool


def fetch_authors(ids: list[str]) -> dict[str, dict]:
    return {short_id(a["id"]): a for a in oa_lookup("authors", "ids.openalex", ids, AUTHOR_SELECT)}


def authors_by_orcid(orcids: list[str]) -> dict[str, list[str]]:
    out = defaultdict(list)
    for a in oa_lookup("authors", "orcid", orcids, "id,orcid", singleton_prefix="orcid:"):
        o = (a.get("orcid") or "").rsplit("/", 1)[-1].upper()
        out[o].append(short_id(a["id"]))
    return out


def works_by_doi(dois: list[str]) -> list[dict]:
    # DOI strings are long: 50 per call keeps the URL a sane size
    return oa_lookup("works", "doi", dois, "id,doi,authorships", batch=50, singleton_prefix="doi:")


# ---------------------------------------------------------------------- scoring
def author_names(a: dict) -> list[str]:
    return [a.get("display_name") or ""] + (a.get("display_name_alternatives") or [])


def best_name_sim(fac_names: list[str], a: dict) -> float:
    """Display name at full weight; OpenAlex's alternative spellings (often initials-only or
    noisy) count 0.1 less."""
    disp = max((name_similarity(f, a.get("display_name") or "") for f in fac_names if f), default=0.0)
    alt = max((name_similarity(f, n) for f in fac_names if f for n in (a.get("display_name_alternatives") or [])), default=0.0)
    return max(disp, alt - 0.1)


def affiliated_years(a: dict, inst_ids: set[str]) -> list[int]:
    ys = []
    for af in a.get("affiliations") or []:
        if short_id(af["institution"]["id"]) in inst_ids:
            ys += af.get("years", [])
    return sorted(set(ys))


def author_fields(a: dict) -> set[str]:
    """OpenAlex fields among the author's top topics (weighted presence, top 5)."""
    return {((t.get("field") or {}).get("display_name") or "") for t in (a.get("topics") or [])[:5]} - {""}


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
    dblp_ok = evid["dblp_trusted"] or evid["inst_affiliated"]
    if evid["dblp_shared"] >= 3 and ns >= 0.75 and dblp_ok and not evid["field_mismatch"]:
        return 0.97, "dblp_doi_overlap>=3"
    if evid["dblp_shared"] >= 1 and ns >= 0.75 and dblp_ok and not evid["field_mismatch"]:
        return 0.88 if evid["inst_affiliated"] else 0.8, "dblp_doi_overlap"
    if ns >= 0.95 and evid.get("last_known_is_institute") and not evid["field_mismatch"]:
        return 0.88, "name+last_known_institution"
    if ns >= 0.95 and evid["inst_affiliated"] and evid["affil_years_in_window"] >= 1:
        c = 0.86
        if evid["field_mismatch"]:
            c = 0.6  # namesake: none of its fields appear in the person's verified profile
        elif evid["topic_overlap"] == 0 and evid["has_area_text"]:
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
    prefetch([p for p in roster.dblp_pid if p])  # batched SPARQL
    for _, r in tqdm(roster.iterrows(), total=len(roster), desc="DBLP person records"):
        if r.dblp_pid:
            try:
                dblp_cache[r.faculty_id] = person_publications(r.dblp_pid)
            except Exception as e:
                log.warning("DBLP %s (%s): %s", r.dblp_pid, r["name"], e)

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

    # DBLP PIDs found only by exact name can be DBLP's undisambiguated catch-all record (e.g. the
    # bare 'Anuj Kumar' entry pools many people). Keep one only if ≥ 3 of its 2016+ DOIs are
    # works that OpenAlex affiliates with the person's institute.
    inst_dois = institution_dois(insts)
    weak = set(roster[roster.dblp_source.eq("dblp_unique_exact_name")].faculty_id)
    for fid in list(dblp_cache):
        if fid not in weak:
            continue
        inst = fid.split(":")[0]
        dois = {d for rec in dblp_cache[fid]["records"] if rec["year"] and rec["year"] >= Y0 for d in rec["dois"]}
        ov = len(dois & inst_dois[inst])
        if ov < 3:
            log.info("dropping DBLP pid %s for %s (only %d of %d DOIs institute-affiliated)", dblp_cache[fid]["pid"], fid, ov, len(dois))
            dblp_cache.pop(fid)
            dblp_hits.pop(fid, None)
            roster.loc[roster.faculty_id == fid, ["dblp_pid", "dblp_source"]] = ["", f"rejected_catchall_or_wrong({ov}_inst_dois)"]
        else:
            roster.loc[roster.faculty_id == fid, "dblp_source"] = f"dblp_exact_name_verified({ov}_inst_dois)"

    # ORCIDs: homepage first, else from the (verified) DBLP person record
    orcid_of = {}
    for _, r in roster.iterrows():
        o = (r.orcid or "").upper()
        dp = dblp_cache.get(r.faculty_id)
        if not o and dp and dp["orcids"]:
            o = dp["orcids"][0].upper()
        if o:
            orcid_of[r.faculty_id] = o
    by_orcid = authors_by_orcid(list(orcid_of.values()))

    # candidate ids per faculty
    cand_ids: dict[str, set[str]] = {}
    searched: set[tuple[str, str]] = set()
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

    # faculty with no strong candidate yet (new joiners publishing under a previous institute):
    # OpenAlex author search by name (10 credits each), restricted to close name matches
    for _, r in roster.iterrows():
        strong = [a for a in cand_ids[r.faculty_id] if a in all_pool and best_name_sim([r["name"]], all_pool[a]) >= 0.9]
        if strong or r.designation_class != "core":
            continue
        try:
            res = oa_get("authors", search=r["name"], select=AUTHOR_SELECT, **{"per-page": 25})
        except Exception as e:
            log.warning("author search failed for %s: %s", r["name"], e)
            continue
        for a in res.get("results", []):
            if best_name_sim([r["name"]], a) >= 0.9:
                all_pool[short_id(a["id"])] = a
                cand_ids[r.faculty_id].add(short_id(a["id"]))
                searched.add((r.faculty_id, short_id(a["id"])))

    # fetch authors not in pool (ORCID/DBLP finds outside the institution)
    missing = {a for ids in cand_ids.values() for a in ids} - set(all_pool)
    all_pool.update(fetch_authors(list(missing)))

    # A DBLP record's DOIs should land on one person's OpenAlex profiles, which share topics.
    # If they scatter over unrelated profiles (an undisambiguated DBLP record pooling several
    # people), keep only the topic cluster anchored by an institute-affiliated or ORCID profile
    # (or a clearly dominant one) and stop trusting the record.
    dblp_catchall: set[str] = set()
    src_of = roster.set_index("faculty_id").dblp_source.to_dict()
    for fid, hits in list(dblp_hits.items()):
        if src_of.get(fid, "").startswith(("homepage", "dblp_affiliation", "dblp_name+affiliation")):
            continue  # linked by the person or matched on DBLP's own affiliation: authoritative, may span areas
        tops = {a: {short_id(t["id"]) for t in (all_pool.get(a) or {}).get("topics", [])[:10]} for a in hits}
        works = {a: (all_pool.get(a) or {}).get("works_count", 0) for a in hits}
        tiny = {a for a in hits if len(tops[a]) < 3 or works[a] < 5}  # too small to show a topic profile
        clusters: list[set[str]] = []
        for a in sorted(set(hits) - tiny, key=lambda x: -hits[x]):
            hit = [c for c in clusters if any(len(tops[a] & tops[b]) >= 2 for b in c)]
            clusters = [c for c in clusters if c not in hit] + [{a}.union(*hit) if hit else {a}]
        weight = lambda c: sum(hits[a] for a in c)  # noqa: E731
        clusters.sort(key=weight, reverse=True)
        if clusters:
            clusters[0] |= tiny  # tiny split profiles follow the dominant cluster
        elif tiny:
            clusters = [set(tiny)]
        sizable = [c for c in clusters if weight(c) >= 3 and sum(works[a] for a in c) >= 10]
        if len(sizable) <= 1:
            keep = clusters[0] if clusters else set()
        else:
            inst = fid.split(":")[0]
            anchored = [c for c in sizable if any(affiliated_years(all_pool.get(a) or {}, all_inst_ids[inst]) or
                        ((all_pool.get(a) or {}).get("orcid") or "").upper().endswith(orcid_of.get(fid, "-")) for a in c)]
            keep = anchored[0] if len(anchored) == 1 else set()
            if len(sizable) >= 3 or not keep:
                dblp_catchall.add(fid)
                log.info("DBLP record for %s scatters over %d unrelated profiles: treated as pooled", fid, len(sizable))
        dblp_hits[fid] = Counter({a: n for a, n in hits.items() if a in keep})

    claims = Counter(a for fid, ids in cand_ids.items() for a in ids
                     if best_name_sim([roster.set_index("faculty_id").at[fid, "name"]], all_pool.get(a, {})) >= 0.95)

    # verified core profile per faculty = IDs found by ORCID or by a trusted DBLP pid; their
    # fields are the reference for spotting namesakes among name-only candidates
    trusted_src = roster.set_index("faculty_id").dblp_source.to_dict()
    def is_trusted(fid):
        if fid in dblp_catchall:
            return False
        src = trusted_src.get(fid, "")
        return bool(src) and not src.startswith("rejected") and src != "dblp_unique_exact_name"  # incl. *_no_homonyms, *_verified
    core_fields: dict[str, set[str]] = defaultdict(set)
    for _, r in roster.iterrows():
        for aid in cand_ids[r.faculty_id]:
            a = all_pool.get(aid) or {}
            orc = bool(orcid_of.get(r.faculty_id)) and (a.get("orcid") or "").upper().endswith(orcid_of[r.faculty_id]) \
                and best_name_sim([r["name"]], a) >= 0.7
            dbl = is_trusted(r.faculty_id) and dblp_hits.get(r.faculty_id, Counter()).get(aid, 0) >= 3
            if orc or dbl:
                core_fields[r.faculty_id] |= author_fields(a)

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
                # ORCID scraped from a homepage can belong to a colleague listed on the same page: require a name match too
                "orcid_match": bool(orcid_of.get(r.faculty_id)) and (a.get("orcid") or "").upper().endswith(orcid_of.get(r.faculty_id, "-"))
                               and best_name_sim([r["name"]] + str(r.name_variants).split("; "), a) >= 0.7,
                "dblp_shared": dblp_hits.get(r.faculty_id, Counter()).get(aid, 0),
                "inst_affiliated": bool(yrs),
                "affil_years_in_window": sum(Y0 <= y <= Y1 for y in yrs),
                "topic_overlap": len(aw & topic_words(a)),
                "has_area_text": bool(aw),
                "n_roster_claims": claims.get(aid, 0),
                "dblp_trusted": is_trusted(r.faculty_id),
                "field_mismatch": bool(core_fields.get(r.faculty_id)) and not (author_fields(a) & core_fields[r.faculty_id]),
                "last_known_is_institute": bool({short_id(i.get("id")) for i in (a.get("last_known_institutions") or [])} & all_inst_ids[r.institution]),
                "from_name_search": (r.faculty_id, aid) in searched,
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
                "top_fields": "; ".join(sorted(author_fields(a))),
                "topic_ids": ";".join(short_id(t["id"]) for t in (a.get("topics") or [])[:10]),
                "research_areas": r.research_areas,
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


def auto_decisions(rev: pd.DataFrame, cands: pd.DataFrame) -> list[str]:
    """Second pass with corroborating evidence, so the pipeline completes without a human;
    every decision is visible and overridable in the review file."""
    hi = cands[cands.confidence >= AUTO]
    prof_topics = hi.groupby("faculty_id").top_topics.apply(lambda s: {t for x in s for t in str(x).split("; ") if t}).to_dict()
    has_ids = set(hi.faculty_id)
    out = []
    for r in rev.itertuples():
        topics = {t for t in str(r.top_topics).split("; ") if t}
        overlap = len(topics & prof_topics.get(r.faculty_id, set()))
        aff = bool(r.inst_affiliated)
        if "SHARED_ID_CONFLICT" in str(r.reason):
            out.append("N (auto: ID claimed by another faculty member; unresolved)")
        elif r.dblp_shared >= 1 and r.name_sim >= 0.75 and aff:
            out.append(f"Y (auto: {r.dblp_shared} DBLP DOIs shared + institute affiliation)")
        elif r.name_sim >= 0.9 and aff and overlap >= 1:
            out.append(f"Y (auto: split profile — name {r.name_sim:.2f}, institute-affiliated, {overlap} shared topics)")
        elif r.faculty_id not in has_ids and r.name_sim >= 0.95 and aff and r.affil_years_in_window >= 1:
            out.append("Y (auto: only candidate — exact name, institute-affiliated in window)")
        elif r.name_sim >= 0.9 and overlap >= 2 and r.works_count <= 30:
            out.append(f"Y (auto: small split profile — name {r.name_sim:.2f}, {overlap} shared topics)")
        else:
            why = "no institute affiliation" if not aff else ("no topic overlap with accepted profiles" if overlap == 0 else "weak name match")
            out.append(f"N (auto: {why})")
    return out


def write_review(cands: pd.DataFrame, insts: dict, roster: pd.DataFrame) -> None:
    _, shared = resolve_shared(cands[cands.confidence >= AUTO], roster)  # only unresolved conflicts
    rev = cands[((cands.confidence < AUTO) & (cands.confidence >= 0.4)) | cands.author_id.isin(shared)].copy()
    rev.loc[rev.author_id.isin(shared), "reason"] = rev.loc[rev.author_id.isin(shared), "reason"] + " | SHARED_ID_CONFLICT"
    ids = {i: set(v["openalex_ids_all"]) for i, v in insts.items()}
    rev["sample_titles"] = [sample_titles(a, ids[i]) for a, i in tqdm(zip(rev.author_id, rev.institution), total=len(rev), desc="sample titles")]
    rev["accept"] = auto_decisions(rev, cands)  # pre-filled "Y/N (auto: why)"; edit and run `make reingest` to override
    cols = ["accept", "faculty_id", "name", "institution", "unit", "author_id", "author_name", "confidence", "reason",
            "name_sim", "orcid_match", "dblp_shared", "affiliated_years", "works_count", "h_index_lifetime",
            "last_known", "top_topics", "sample_titles", "n_roster_claims"]
    rev.sort_values(["institution", "name", "confidence"], ascending=[True, True, False])[cols].to_csv(
        REVIEW / "author_matches_to_review.csv", index=False)


def resolve_shared(hi: pd.DataFrame, roster: pd.DataFrame) -> tuple[pd.DataFrame, set[str]]:
    """An OpenAlex ID claimed by several faculty records:
      * same person in both institutes' rosters (moved, or adjunct at the other) -> keep for all;
      * else give it to the only claimant whose institute the profile is affiliated with, or to
        a claimant whose name matches clearly better (≥ 0.15);
      * else nobody (left for review)."""
    names = roster.set_index("faculty_id").name.to_dict()
    keep, unresolved = [], set()
    for aid, g in hi.groupby("author_id"):
        if g.faculty_id.nunique() == 1:
            keep.append(g)
            continue
        fids = g.faculty_id.unique().tolist()
        same_person = all(name_similarity(names[fids[0]], names[f]) >= 0.95 for f in fids[1:]) and len({f.split(":")[0] for f in fids}) == len(fids)
        if same_person:
            keep.append(g)
            continue
        aff = g[g.inst_affiliated.astype(bool)]
        if aff.faculty_id.nunique() == 1:
            keep.append(aff)
            continue
        top = g.sort_values("name_sim", ascending=False)
        if len(top) > 1 and top.name_sim.iloc[0] - top.name_sim.iloc[1] >= 0.15:
            keep.append(top.head(1))
            continue
        unresolved.add(aid)
    return (pd.concat(keep) if keep else hi.head(0)), unresolved


ANCHOR_REASONS = ("orcid", "dblp_doi_overlap>=3")


def _topics(x) -> set[str]:
    return {t for t in str(x).split(";") if t}


def cluster_filter(acc: pd.DataFrame, cands: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Keep weak (name-based) matches only when they are topically consistent with the person.

    * anchor = IDs accepted on ORCID or trusted DBLP overlap; a weak ID needs ≥ 2 of its top-10
      topics among the anchors' topics (split profiles of one person share topics);
    * no anchor: group the weak IDs into topic clusters (≥ 2 shared topics = same cluster);
      one cluster -> keep it; several -> the person's homepage research areas pick the cluster
      by word overlap with topic names, else drop all (an ambiguous name is not guessed)."""
    info = cands.drop_duplicates(["faculty_id", "author_id"]).set_index(["faculty_id", "author_id"])
    keep, dropped = [], []
    for fid, g in acc.groupby("faculty_id"):
        anchors = g[g.reason.isin(ANCHOR_REASONS)]
        weak = g[~g.reason.isin(ANCHOR_REASONS)]
        if weak.empty:
            keep.append(g)
            continue
        top = lambda aid: _topics(info.loc[(fid, aid), "topic_ids"]) if (fid, aid) in info.index else set()  # noqa: E731
        if len(anchors):
            ref = set().union(*(top(a) for a in anchors.author_id))
            ok = weak[weak.author_id.map(lambda a: len(top(a) & ref) >= 2 or not top(a))]
            keep += [anchors, ok]
            dropped += [{"faculty_id": fid, "author_id": a, "why": "topics inconsistent with ORCID/DBLP-anchored profile"} for a in set(weak.author_id) - set(ok.author_id)]
            continue
        # cluster weak IDs by topic overlap (single-link)
        ids = list(weak.author_id)
        clusters: list[set[str]] = []
        for a in ids:
            hit = [c for c in clusters if any(len(top(a) & top(b)) >= 2 for b in c)]
            merged = {a}.union(*hit) if hit else {a}
            clusters = [c for c in clusters if c not in hit] + [merged]
        works = lambda c: sum(int(info.loc[(fid, a), "works_count"]) if (fid, a) in info.index else 0 for a in c)  # noqa: E731
        big = [c for c in clusters if works(c) >= 5]
        if len(big) <= 1:
            chosen = big[0] if big else set(ids)
        else:
            areas = set(re.findall(r"[a-z]{4,}", str(info.loc[(fid, ids[0]), "research_areas"]).lower())) - {"research", "systems", "analysis"}
            def score(c):
                names = " ".join(str(info.loc[(fid, a), "top_topics"]) for a in c if (fid, a) in info.index).lower()
                return sum(1 for w in areas if w in names)
            ranked = sorted(big, key=score, reverse=True)
            chosen = ranked[0] if areas and score(ranked[0]) >= 2 and score(ranked[0]) > score(ranked[1]) else set()
        keep.append(weak[weak.author_id.isin(chosen)])
        dropped += [{"faculty_id": fid, "author_id": a, "why": "ambiguous name: several topic clusters" if len(big) > 1 else "small unrelated profile"}
                    for a in set(ids) - set(chosen)]
    return (pd.concat(keep) if keep else acc.head(0)), dropped


def finalise(cands: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    hi, shared = resolve_shared(cands[cands.confidence >= AUTO], roster)
    if shared:
        log.warning("author ids claimed by >1 faculty and unresolved (sent to review): %s", sorted(shared))
    acc = hi[["faculty_id", "author_id", "confidence", "reason"]].assign(decided_by="auto")
    rp = REVIEW / "author_matches_to_review.csv"
    if rp.exists():
        rev = pd.read_csv(rp, dtype=str).fillna("")
        yes = rev[rev.accept.str.strip().str.upper().str.match(r"^Y(ES)?\b")]
        acc = pd.concat([acc, yes[["faculty_id", "author_id", "confidence", "reason"]].assign(
            decided_by=yes.accept.map(lambda x: "auto_second_pass" if "auto:" in x else "manual_review"))])
        no = rev[rev.accept.str.strip().str.upper().str.match(r"^N(O)?\b")]
        acc = acc.merge(no[["faculty_id", "author_id"]], how="left", indicator=True)
        acc = acc[acc._merge == "left_only"].drop(columns="_merge")
    extra = REVIEW / "author_ids_manual_add.csv"  # optional: faculty_id,author_id you add by hand
    if extra.exists():
        acc = pd.concat([acc, pd.read_csv(extra, dtype=str).assign(confidence=1.0, reason="manual_add", decided_by="manual_add")])
    acc = acc.drop_duplicates(["faculty_id", "author_id"])
    manual = acc[acc.decided_by.isin(["manual_review", "manual_add"])]
    acc, dropped = cluster_filter(acc[~acc.index.isin(manual.index)], cands)
    acc = pd.concat([acc, manual]).drop_duplicates(["faculty_id", "author_id"])  # your own decisions are never filtered
    pd.DataFrame(dropped).to_csv(REVIEW / "author_matches_dropped_by_topic_check.csv", index=False)
    log.info("topic-consistency filter dropped %d weak matches", len(dropped))
    acc.to_csv(PROCESSED / "faculty_author_ids.csv", index=False)
    return acc


def update_roster(roster: pd.DataFrame, acc: pd.DataFrame, cands: pd.DataFrame, insts: dict) -> pd.DataFrame:
    ids = acc.groupby("faculty_id").author_id.apply(lambda s: "; ".join(sorted(s)))
    roster["openalex_ids"] = roster.faculty_id.map(ids).fillna("")
    # joining-year fallback: first institute-affiliated year (after PhD year if known)
    inst_ids = {i: set(v["openalex_ids_all"]) for i, v in insts.items()}
    c = cands.merge(acc[["faculty_id", "author_id"]])
    for i, r in roster.iterrows():
        if r.joining_year:
            continue
        yrs = sorted({int(y) for s in c[c.faculty_id == r.faculty_id].affiliated_years for y in str(s).split(",") if y})
        phd = re.search(r"((?:19|20)\d{2})", str(r.phd or ""))
        if phd:  # institute affiliation during a PhD there is not employment
            yrs = [y for y in yrs if y >= int(phd.group(1))]
        if r.get("joined_after_year"):  # absent from every archived list up to that year
            yrs = [y for y in yrs if y >= int(float(r.joined_after_year))]
        if r.get("joined_by_year"):
            continue  # on the earliest archived list: joined before the window, exact year not needed
        if yrs:
            roster.at[i, "joining_year"] = str(yrs[0])
            roster.at[i, "joining_year_source"] = "inferred_first_affiliated_paper"
            roster.at[i, "joining_year_confidence"] = "0.5"
        elif r.get("joined_after_year"):
            roster.at[i, "joining_year"] = str(int(float(r.joined_after_year)))
            roster.at[i, "joining_year_source"] = "wayback_absent_until"
            roster.at[i, "joining_year_confidence"] = "0.4"
    roster.to_csv(DATA / "faculty_roster.csv", index=False)
    return roster


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reingest", action="store_true")
    args = ap.parse_args()
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    insts = json.loads((PROCESSED / "institutions.json").read_text()) if args.reingest else resolve_institutions()
    if args.reingest:
        cands = pd.read_parquet(PROCESSED / "author_candidates.parquet")
    else:
        cands = resolve(roster, insts)
        write_review(cands, insts, roster)
    acc = finalise(cands, roster)
    roster = update_roster(roster, acc, cands, insts)

    core = roster[roster.is_core.eq("True")]
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
