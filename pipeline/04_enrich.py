"""Step 4 — Enrichment: type, venue normalisation, SJR quartile, CORE rank, citations
(OpenAlex + Semantic Scholar), topics, co-author institutes, Indian citation flags in both
directions, partner classification, h-index.

Manual inputs (the pipeline never scrapes these; see README):
  data/external/scimago/*.csv   Scimago journal rank exports, one per year 2016–2025
  data/external/core/*.csv      CORE conference ranking exports (one or more editions)
Optional hand-check files (created on first run, edits respected on re-run):
  data/external/venue_overrides.csv     venue_key -> canonical_venue, acronym
  data/external/core_overrides.csv      venue_key or acronym -> core_rank
  data/external/partner_type_map.csv    institution -> partner_type (checked=Y rows win)
"""
from __future__ import annotations

import glob
import gzip
import json
import re
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process
from tqdm import tqdm

from common.config import DATA, EXTERNAL, PROCESSED, REVIEW, cfg, setup_logging
from common.http import BudgetExhausted
from common.partners import classify
from common.quartile_proxy import proxy_quartiles
from common.sources import OA_MAX_OR, chunks, crossref, oa_get, oa_lookup, oa_paginate, s2, short_id
from common.titles import is_arxiv_doi
from common.venues import dblp_acronym, extract_acronym, venue_key

log = setup_logging("04_enrich")
Y0, Y1 = cfg()["years"]["start"], cfg()["years"]["end"]


def load():
    papers = pd.read_parquet(PROCESSED / "papers.parquet")
    links = pd.read_parquet(PROCESSED / "faculty_paper_links.parquet")
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    insts = json.loads((PROCESSED / "institutions.json").read_text())
    works = {}
    with gzip.open(PROCESSED / "works_openalex.jsonl.gz", "rt") as fh:
        for line in fh:
            w = json.loads(line)
            works[short_id(w["id"])] = w
    return papers, links, roster, insts, works


# ------------------------------------------------------------------ Crossref
def crossref_meta(dois: list[str]) -> dict[str, dict]:
    out = {}
    for d in tqdm(dois, desc="Crossref by DOI"):
        try:
            m = crossref().get(f"https://api.crossref.org/works/{d}").get("message", {})
        except Exception as e:
            log.info("crossref %s: %s", d, e)
            continue
        issns = {i["value"].replace("-", "").upper(): i.get("type") for i in m.get("issn-type", [])}
        out[d] = {"cr_type": m.get("type"), "cr_container": (m.get("container-title") or [""])[0],
                  "cr_issns": ";".join(issns), "cr_event": (m.get("event") or {}).get("name", "")}
    return out


# ------------------------------------------------------------------ type
def decide_type(row, w) -> tuple[str, str]:
    votes = []
    if row.is_preprint_only:
        return "preprint", "all_records_preprint"
    if row.dblp_type in ("journal", "conference"):
        votes.append(("dblp", row.dblp_type))
    src = ((w or {}).get("primary_location") or {}).get("source") or {}
    st, wt = src.get("type"), (w or {}).get("type")
    if st == "journal" and wt in ("article", "review", None):
        votes.append(("openalex", "journal"))
    elif st == "conference" or (st == "book series" and re.search(r"lecture notes|proceedings|ceur|pmlr|lipics", (src.get("display_name") or ""), re.I)):
        votes.append(("openalex", "conference"))
    ct = row.get("cr_type") or ""
    if ct == "journal-article":
        votes.append(("crossref", "journal"))
    elif ct == "proceedings-article" or (ct == "book-chapter" and re.search(r"proceedings|conference|symposium|workshop", row.get("cr_container") or "", re.I)):
        votes.append(("crossref", "conference"))
    if row.portal_type in ("journal", "conference"):
        votes.append(("portal", row.portal_type))
    desc = ";".join(f"{s}={t}" for s, t in votes)
    if not votes:
        return ("other", f"openalex_type={wt};source_type={st};crossref={ct}")
    if votes[0][0] == "dblp":  # DBLP wins for CS venues
        return votes[0][1], desc
    c = Counter(t for _, t in votes)
    return c.most_common(1)[0][0], desc


# ------------------------------------------------------------------ venues
def venue_names(row, w) -> list[str]:
    src = ((w or {}).get("primary_location") or {}).get("source") or {}
    return [n for n in (src.get("display_name"), row.dblp_venue, row.get("cr_container"), row.portal_venue) if n]


def build_venue_map(papers: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in papers.itertuples():
        rows.append({"venue_key": r.venue_key, "raw": r.venue_raw, "acr_dblp": dblp_acronym(r.dblp_venue_key),
                     "acr_extract": extract_acronym(r.venue_raw) or extract_acronym(r.cr_event or ""),
                     "acr_portal": r.portal_acronym or "", "type": r.type, "issns": r.issns})
    df = pd.DataFrame(rows)
    df = df[df.venue_key.ne("")]
    out = []
    for k, g in df.groupby("venue_key"):
        acr = Counter([a for a in g.acr_dblp if a] or [a for a in g.acr_extract if a] or [a for a in g.acr_portal if a])
        out.append({"venue_key": k, "canonical_venue": Counter(g.raw).most_common(1)[0][0],
                    "acronym": acr.most_common(1)[0][0] if acr else "", "n_papers": len(g),
                    "type_mode": Counter(g.type).most_common(1)[0][0],
                    "issns": ";".join(sorted({i for s in g.issns for i in str(s).split(";") if i})),
                    "raw_variants": " | ".join(list(dict.fromkeys(g.raw))[:5])})
    vm = pd.DataFrame(out).sort_values("n_papers", ascending=False)
    ov = EXTERNAL / "venue_overrides.csv"
    if ov.exists():
        o = pd.read_csv(ov, dtype=str).fillna("")
        for r in o.itertuples():
            m = vm.venue_key.eq(r.venue_key)
            if r.canonical_venue:
                vm.loc[m, "canonical_venue"] = r.canonical_venue
            if r.acronym:
                vm.loc[m, "acronym"] = r.acronym
        vm["hand_checked"] = vm.venue_key.isin(o.venue_key)
    else:
        vm["hand_checked"] = False
    return vm


# ------------------------------------------------------------------ Scimago
def load_scimago() -> dict[str, dict[int, tuple[str, str, str]]]:
    """issn -> year -> (best_quartile, category_used, journal_title)."""
    files = sorted(glob.glob(str(EXTERNAL / "scimago" / "*.csv")))
    idx: dict[str, dict[int, tuple]] = defaultdict(dict)
    for f in files:
        m = re.search(r"(20\d{2})", f.rsplit("/", 1)[-1])
        if not m:
            log.warning("cannot infer year from %s", f)
            continue
        yr = int(m.group(1))
        df = pd.read_csv(f, sep=";", dtype=str, encoding="utf-8", on_bad_lines="skip").fillna("")
        qcol = next(c for c in df.columns if "Best Quartile" in c)
        for _, r in df.iterrows():
            q = r[qcol]
            if q not in ("Q1", "Q2", "Q3", "Q4"):
                continue
            cats = r.get("Categories", "")
            cat_used = next((c.strip() for c in cats.split(";") if f"({q})" in c), "")
            for issn in str(r.get("Issn", "")).split(","):
                issn = issn.strip().upper()
                if len(issn) == 8 and issn != "00000000":
                    idx[issn][yr] = (q, cat_used, r.get("Title", ""))
    log.info("Scimago: %d files, %d ISSNs", len(files), len(idx))
    return idx


def quartile_for(issns: list[str], year: int, sj: dict) -> tuple[str, str, int | None, str]:
    """Best quartile across the paper's ISSNs for its year; nearest available year otherwise."""
    best = None
    for i in issns:
        yrs = sj.get(i)
        if not yrs:
            continue
        y = year if year in yrs else min(yrs, key=lambda k: (abs(k - year), -k))
        q, cat, title = yrs[y]
        cand = (q, cat, y, "exact_year" if y == year else "nearest_year")
        if best is None or q < best[0]:
            best = cand
    return best or ("", "", None, "")


# ------------------------------------------------------------------ CORE
EDITION_YEAR = {"CORE2008": 2008, "ERA2010": 2010, "CORE2013": 2013, "CORE2014": 2014, "CORE2017": 2017, "CORE2018": 2018,
                "CORE2020": 2020, "CORE2021": 2021, "CORE2023": 2023, "ICORE2026": 2026}


def load_core() -> pd.DataFrame:
    files = sorted(glob.glob(str(EXTERNAL / "core" / "*.csv")))
    frames = []
    for f in files:
        df = pd.read_csv(f, header=None, dtype=str).fillna("")
        df = df.iloc[:, :5]
        df.columns = ["core_id", "title", "acronym", "edition", "rank"]
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=["core_id", "title", "acronym", "edition", "rank", "edition_year", "key"])
    core = pd.concat(frames).drop_duplicates()
    core["edition_year"] = core.edition.map(EDITION_YEAR).fillna(0).astype(int)
    core["key"] = core.title.map(venue_key)
    core = core[core["rank"].isin(["A*", "A", "B", "C", "Australasian A", "Australasian B", "Australasian C", "National", "Regional", "Unranked", "TBR"])]
    log.info("CORE: %d rows, editions %s", len(core), sorted(core.edition.unique()))
    return core


def core_match(vm: pd.DataFrame, core: pd.DataFrame) -> dict[str, dict]:
    """venue_key -> {edition_year: rank, ...} plus method. Acronym first, then fuzzy title."""
    out = {}
    if core.empty:
        return out
    ov = {}
    ovp = EXTERNAL / "core_overrides.csv"
    if ovp.exists():
        for r in pd.read_csv(ovp, dtype=str).fillna("").itertuples():
            ov[r.key] = r.core_rank
    by_acr = defaultdict(list)
    for r in core.itertuples():
        by_acr[r.acronym.upper()].append(r)
    keys = core.key.unique().tolist()
    for v in vm[vm.type_mode.eq("conference")].itertuples():
        if v.venue_key in ov or v.acronym in ov:
            out[v.venue_key] = {"ranks": {9999: ov.get(v.venue_key) or ov.get(v.acronym)}, "method": "manual_override", "core_title": ""}
            continue
        hits, method = [], ""
        if v.acronym and v.acronym.upper() in by_acr:
            cands = by_acr[v.acronym.upper()]
            # acronyms collide across fields: confirm with a loose title check
            ok = [c for c in cands if fuzz.token_set_ratio(v.venue_key, c.key) >= 60] or (cands if len({c.core_id for c in cands}) == 1 else [])
            if ok:
                hits, method = ok, "acronym"
        if not hits:
            m = process.extractOne(v.venue_key, keys, scorer=fuzz.token_sort_ratio, score_cutoff=92)
            if m:
                hits, method = core[core.key.eq(m[0])].itertuples(), f"fuzzy_title({m[1]:.0f})"
                hits = list(hits)
        if hits:
            out[v.venue_key] = {"ranks": {h.edition_year: h.rank for h in hits}, "method": method, "core_title": hits[0].title}
    return out


def core_rank_for(match: dict | None, year: int) -> tuple[str, str]:
    """Edition in force at publication time: latest edition <= year, else the earliest one."""
    if not match:
        return "", ""
    ranks = match["ranks"]
    if 9999 in ranks:
        return ranks[9999], "manual_override"
    eds = sorted(ranks)
    prior = [e for e in eds if e <= year]
    e = prior[-1] if prior else eds[0]
    return ranks[e], f"CORE{e}" if e else "CORE?"


# ------------------------------------------------------------------ Semantic Scholar
def s2_citations(dois: list[str]) -> dict[str, int]:
    out = {}
    for ch in tqdm(list(chunks(sorted(set(dois)), 500)), desc="Semantic Scholar batch"):
        try:
            res = s2().get("https://api.semanticscholar.org/graph/v1/paper/batch",
                           params={"fields": "citationCount,externalIds"}, json_body={"ids": [f"DOI:{d}" for d in ch]})
        except Exception as e:
            log.warning("S2 batch failed (%s); continuing without S2 for this chunk", e)
            continue
        for d, rec in zip(ch, res):
            if rec and rec.get("citationCount") is not None:
                out[d] = rec["citationCount"]
    return out


# ------------------------------------------------------------------ institutions helpers
def inst_list(w: dict) -> list[dict]:
    seen, out = set(), []
    for au in (w or {}).get("authorships", []):
        for i in au.get("institutions", []):
            k = short_id(i.get("id")) or i.get("display_name")
            if k and k not in seen:
                seen.add(k)
                out.append({"id": short_id(i.get("id")), "name": i.get("display_name", ""), "cc": i.get("country_code") or "",
                            "type": i.get("type") or "", "lineage": [short_id(x) for x in i.get("lineage", [])]})
    return out


def is_own(inst: dict, own_ids: set[str]) -> bool:
    return bool({inst["id"], *inst["lineage"]} & own_ids)


# ------------------------------------------------------------------ main
def main() -> None:
    papers, links, roster, insts, works = load()
    inst_ids = {i: set(v["openalex_ids_all"]) for i, v in insts.items()}
    all_own = set().union(*inst_ids.values())
    paper_insts = links[links.in_main_set].groupby("paper_id").institution.apply(lambda s: sorted(set(s)))
    papers["our_institutions"] = papers.paper_id.map(paper_insts).apply(lambda x: x if isinstance(x, list) else [])

    # Crossref for DOIs where OpenAlex lacks ISSN/venue/type, and for non-OpenAlex papers
    need = []
    for r in papers.itertuples():
        w = works.get(r.openalex_id) if r.openalex_id else None
        src = ((w or {}).get("primary_location") or {}).get("source") or {}
        if r.doi and not is_arxiv_doi(r.doi) and (not w or not src.get("issn") or not src.get("display_name")):
            need.append(r.doi)
    cr = crossref_meta(need)
    for col in ("cr_type", "cr_container", "cr_issns", "cr_event"):
        papers[col] = papers.doi.map(lambda d: cr.get(d, {}).get(col, "") if d else "")

    # type, venue, issn
    types, tsrc, vraw, issns, src_ids = [], [], [], [], []
    for r in papers.itertuples():
        w = works.get(r.openalex_id) if r.openalex_id else None
        t, s = decide_type(papers.loc[r.Index], w)
        types.append(t)
        tsrc.append(s)
        names = venue_names(papers.loc[r.Index], w)
        # for conferences prefer the DBLP / portal name (cleaner than OpenAlex proceedings titles)
        pick = (r.dblp_venue if t == "conference" and r.dblp_venue else None) or (names[0] if names else "")
        vraw.append(pick)
        src = ((w or {}).get("primary_location") or {}).get("source") or {}
        iss = {x.replace("-", "").upper() for x in (src.get("issn") or []) if x}
        iss |= {x for x in str(r.cr_issns).split(";") if x}
        issns.append(";".join(sorted(iss)))
        src_ids.append(short_id(src.get("id")))
    papers["type"], papers["type_evidence"], papers["venue_raw"], papers["issns"], papers["openalex_source_id"] = types, tsrc, vraw, issns, src_ids
    papers["venue_key"] = papers.venue_raw.map(venue_key)
    vm = build_venue_map(papers)
    papers = papers.merge(vm[["venue_key", "canonical_venue", "acronym"]], on="venue_key", how="left")
    papers["journal_name"] = papers.canonical_venue.fillna(papers.venue_raw)
    papers["issn"] = papers.issns.map(lambda s: "; ".join(f"{x[:4]}-{x[4:]}" for x in s.split(";") if len(x) == 8))

    # quartile
    sj = load_scimago()
    q = [quartile_for(r.issns.split(";") if r.issns else [], int(r.year or Y1), sj) if r.type == "journal" else ("", "", None, "")
         for r in papers.itertuples()]
    papers["quartile"], papers["sjr_category"], papers["sjr_year_used"], papers["quartile_rule"] = zip(*q) if q else ([], [], [], [])

    # proxy quartile (OpenAlex impact within field) — only a fallback, kept in its own column
    jsrc = sorted({x for x in papers[papers.type.eq("journal")].openalex_source_id.dropna() if x})
    prox = proxy_quartiles(jsrc) if jsrc else {}
    papers["quartile_proxy_openalex"] = papers.openalex_source_id.map(lambda x: prox.get(x, {}).get("quartile_proxy_openalex", "") if x else "")
    papers.loc[~papers.type.eq("journal"), "quartile_proxy_openalex"] = ""
    papers["quartile_source"] = np.where(papers.quartile.ne(""), "scimago_sjr", np.where(papers.quartile_proxy_openalex.ne(""), "openalex_proxy", ""))

    # CORE
    core = load_core()
    cm = core_match(vm, core)
    cr_ = [core_rank_for(cm.get(r.venue_key), int(r.year or Y1)) if r.type == "conference" else ("", "") for r in papers.itertuples()]
    papers["core_rank"], papers["core_edition"] = zip(*cr_) if cr_ else ([], [])
    papers["core_match_method"] = papers.venue_key.map(lambda k: cm.get(k, {}).get("method", ""))
    vm["core_rank_latest"] = vm.venue_key.map(lambda k: cm[k]["ranks"][max(cm[k]["ranks"])] if k in cm else "")
    vm["core_match_method"] = vm.venue_key.map(lambda k: cm.get(k, {}).get("method", ""))
    vm["core_title"] = vm.venue_key.map(lambda k: cm.get(k, {}).get("core_title", ""))
    vm.to_csv(EXTERNAL / "venue_map.csv", index=False)
    vm.head(150).to_csv(REVIEW / "venue_map_top150_to_check.csv", index=False)

    # citations
    papers["citations_openalex"] = papers.openalex_id.map(lambda i: (works.get(i) or {}).get("cited_by_count") if i else None)
    s2c = s2_citations([d for d in papers.doi.dropna() if not is_arxiv_doi(d)])
    papers["citations_s2"] = papers.doi.map(s2c)
    papers["citations_max"] = papers[["citations_openalex", "citations_s2"]].max(axis=1)
    papers["citations_mean"] = papers[["citations_openalex", "citations_s2"]].mean(axis=1)
    papers["citations"] = papers.citations_openalex.fillna(papers.citations_s2)

    # topics
    def topic(i, lvl):
        t = (works.get(i) or {}).get("primary_topic") or {}
        return (t if lvl == "topic" else (t.get(lvl) or {})).get("display_name", "") if t else ""
    for lvl in ("topic", "subfield", "field", "domain"):
        papers[f"{lvl}"] = papers.openalex_id.map(lambda i, l=lvl: topic(i, l) if i else "")
    papers["topic_id"] = papers.openalex_id.map(lambda i: short_id(((works.get(i) or {}).get("primary_topic") or {}).get("id")) if i else "")
    papers["n_authors"] = papers.openalex_id.map(lambda i: len((works.get(i) or {}).get("authorships", [])) if i else None)

    # co-author institutes
    ci, cc = [], []
    for r in papers.itertuples():
        il = inst_list(works.get(r.openalex_id)) if r.openalex_id else []
        ci.append("; ".join(i["name"] for i in il))
        cc.append("; ".join(i["cc"] for i in il))
    papers["coauthor_institutes"], papers["coauthor_countries"] = ci, cc

    # ---- Indian citations: outgoing (cites_indian_inst)
    refs = {wid for wid in papers.openalex_id.dropna() for wid in (works.get(wid) or {}).get("referenced_works", [])}
    refs = sorted(short_id(x) for x in refs)
    ref_insts: dict[str, list[dict]] = {}
    ref_rows = []
    for w in tqdm(oa_lookup("works", "openalex_id", refs, select="id,doi,authorships,publication_year"), desc="referenced works"):
        il = inst_list(w)
        ref_insts[short_id(w["id"])] = il
        ref_rows.append({"ref_id": short_id(w["id"]), "doi": (w.get("doi") or "").replace("https://doi.org/", "").lower() or None,
                         "year": w.get("publication_year"), "inst_names": "; ".join(i["name"] for i in il),
                         "inst_ids": ";".join(i["id"] or "" for i in il), "inst_ccs": "; ".join(i["cc"] for i in il),
                         "inst_lineage": ";".join(sorted({x for i in il for x in i["lineage"] if x}))})
    pd.DataFrame(ref_rows).to_parquet(PROCESSED / "referenced_works.parquet", index=False)
    flags, lists, counts, given = [], [], [], defaultdict(Counter)
    for r in papers.itertuples():
        own = set().union(*(inst_ids[i] for i in r.our_institutions)) if r.our_institutions else all_own
        found, n = Counter(), 0
        for ref in (works.get(r.openalex_id) or {}).get("referenced_works", []) if r.openalex_id else []:
            ind = [i for i in ref_insts.get(short_id(ref), []) if i["cc"] == "IN" and not is_own(i, own)]
            if ind:
                n += 1
                for i in ind:
                    found[i["name"]] += 1
        flags.append(n > 0)
        lists.append("; ".join(found))
        counts.append(n)
        for inst in r.our_institutions:
            for name, k in found.items():
                given[inst][name] += k
    papers["cites_indian_inst"], papers["cited_indian_institutions"], papers["n_refs_indian_other"] = flags, lists, counts

    # ---- Indian citations: incoming (cited_by_indian_inst), batched 'cites:' queries
    ours = sorted(papers.openalex_id.dropna().unique())
    ourset = set(ours)
    cited_by = defaultdict(Counter)  # paper -> (inst id, name) -> citing works
    edges = []                       # one row per (cited paper, citing work, Indian institution)
    partner_meta = {}
    for ch in tqdm(list(chunks([p for p in ours if (works.get(p) or {}).get("cited_by_count", 0) > 0], OA_MAX_OR)), desc="citing works (IN)"):
        flt = "cites:" + "|".join(ch) + ",authorships.institutions.country_code:IN"
        try:
            for cw in oa_paginate("works", flt, select="id,publication_year,referenced_works,authorships"):
                targets = {short_id(x) for x in cw.get("referenced_works", [])} & set(ch)
                il = [i for i in inst_list(cw) if i["cc"] == "IN"]
                for t in targets:
                    for i in il:
                        cited_by[t][(i["id"], i["name"])] += 1
                        partner_meta[i["name"]] = i
                        edges.append({"cited_paper": t, "citing_work": short_id(cw["id"]), "citing_year": cw.get("publication_year"),
                                      "partner_id": i["id"], "partner": i["name"], "partner_lineage": ";".join(i["lineage"])})
        except BudgetExhausted:
            raise  # nothing lost: completed pages are cached; re-run after the daily reset
    pinsts = papers.set_index("openalex_id").our_institutions.to_dict()
    yr = papers.set_index("openalex_id").year.to_dict()
    flags, lists, counts = [], [], []
    for r in papers.itertuples():
        own = set().union(*(inst_ids[i] for i in r.our_institutions)) if r.our_institutions else all_own
        c = {k: v for k, v in cited_by.get(r.openalex_id, {}).items() if not ({k[0]} | set(partner_meta.get(k[1], {}).get("lineage", []))) & own}
        flags.append(bool(c))
        lists.append("; ".join(f"{n} ({v})" for (_, n), v in sorted(c.items(), key=lambda kv: -kv[1])))
        counts.append(sum(c.values()))
    papers["cited_by_indian_inst"], papers["citing_indian_institutions"], papers["n_citing_indian_other"] = flags, lists, counts

    # partner-level tables used by step 5
    received = defaultdict(Counter)
    for pid, c in cited_by.items():
        for inst in pinsts.get(pid, []):
            own = inst_ids[inst]
            for (iid, name), v in c.items():
                if not ({iid} | set(partner_meta.get(name, {}).get("lineage", []))) & own:
                    received[inst][name] += v
    pd.DataFrame([{"our_inst": i, "partner": n, "citations_received": v} for i, c in received.items() for n, v in c.items()]).to_parquet(PROCESSED / "citations_received_by_partner.parquet")
    pd.DataFrame([{"our_inst": i, "partner": n, "citations_given": v} for i, c in given.items() for n, v in c.items()]).to_parquet(PROCESSED / "citations_given_to_partner.parquet")
    # every incoming Indian citation edge with its year (year-wise flow is computed in step 5)
    pd.DataFrame(edges).to_parquet(PROCESSED / "citing_indian_edges.parquet", index=False)

    # partner classification
    names = set(papers.coauthor_institutes.str.split("; ").explode().dropna()) | set(partner_meta)
    cc_map = {}
    for r in papers.itertuples():
        for n, c in zip(str(r.coauthor_institutes).split("; "), str(r.coauthor_countries).split("; ")):
            cc_map[n] = c
    meta_types = {i["name"]: i["type"] for w in works.values() for i in inst_list(w)} | {n: m["type"] for n, m in partner_meta.items()}
    pm_path = EXTERNAL / "partner_type_map.csv"
    checked = {}
    if pm_path.exists():
        old = pd.read_csv(pm_path, dtype=str).fillna("")
        checked = dict(zip(old[old.checked.str.upper().eq("Y")].institution, old[old.checked.str.upper().eq("Y")].partner_type))
    pm = []
    for n in sorted(x for x in names if x and (cc_map.get(x) == "IN" or n in partner_meta)):
        t, rule = classify(n, meta_types.get(n), checked)
        pm.append({"institution": n, "partner_type": t, "rule": rule, "openalex_type": meta_types.get(n, ""),
                   "checked": "Y" if n in checked else ""})
    pd.DataFrame(pm).to_csv(pm_path, index=False)

    # h-index (lifetime, per OpenAlex author id) -> roster
    ids = pd.read_csv(PROCESSED / "faculty_author_ids.csv", dtype=str)
    auth = {short_id(a["id"]): a for a in oa_lookup("authors", "ids.openalex", ids.author_id.tolist(), select="id,summary_stats,works_count,cited_by_count")}
    ids["h_lifetime"] = ids.author_id.map(lambda a: ((auth.get(a) or {}).get("summary_stats") or {}).get("h_index"))
    h = ids.groupby("faculty_id").h_lifetime.max()
    roster["h_index_lifetime_openalex"] = roster.faculty_id.map(h)
    roster.to_csv(DATA / "faculty_roster.csv", index=False)

    papers = papers.drop(columns=["our_institutions"]).assign(our_institutions=papers.our_institutions.map(";".join))
    papers.to_parquet(PROCESSED / "papers_enriched.parquet", index=False)

    j = papers[papers.type.eq("journal")]
    c = papers[papers.type.eq("conference")]
    print("\n=== ENRICHMENT SUMMARY ===")
    print("type:", papers.type.value_counts().to_dict())
    print(f"journals with quartile: {j.quartile.ne('').mean():.1%}  (Scimago files: {len(glob.glob(str(EXTERNAL/'scimago'/'*.csv')))})")
    print(f"conferences with CORE rank: {c.core_rank.ne('').mean():.1%}  (CORE files: {len(glob.glob(str(EXTERNAL/'core'/'*.csv')))})")
    print(f"DOI coverage: {papers.doi.notna().mean():.1%}; S2 citations: {papers.citations_s2.notna().mean():.1%}")
    print(f"cites_indian_inst TRUE: {papers.cites_indian_inst.mean():.1%}; cited_by_indian_inst TRUE: {papers.cited_by_indian_inst.mean():.1%}")


if __name__ == "__main__":
    main()
