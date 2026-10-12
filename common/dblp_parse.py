"""DBLP via its official SPARQL endpoint (https://sparql.dblp.org; robots.txt allows /sparql,
Crawl-delay 10). The HTML/XML/JSON API on dblp.org now sits behind a bot-check challenge,
which we do not try to get around; SPARQL is DBLP's supported machine interface.

Queries are batched (many PIDs per query) and every response is cached.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from .http import Fetcher
from .titles import normalise_doi

log = logging.getLogger("dblp")
ENDPOINT = "https://sparql.dblp.org/sparql"
PREFIX = "PREFIX dblp: <https://dblp.org/rdf/schema#>\nPREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
_pub_cache: dict[str, dict] = {}


@lru_cache(maxsize=None)
def _fetcher() -> Fetcher:
    return Fetcher("dblp_sparql", interval=10.0, headers={"Accept": "application/sparql-results+json"}, timeout=120)


def sparql(query: str) -> list[dict]:
    res = _fetcher().get(ENDPOINT, params={"query": PREFIX + query})
    return [{k: v["value"] for k, v in b.items()} for b in res.get("results", {}).get("bindings", [])]


def pid_of(uri: str) -> str:
    return uri.split("/pid/", 1)[-1]


def persons_by_affiliation(patterns: list[str]) -> list[dict]:
    """Every DBLP person whose (any) affiliation string contains one of `patterns`."""
    flt = " || ".join(f'CONTAINS(LCASE(?aff), "{p.lower()}")' for p in patterns)
    rows = sparql(f"""SELECT ?p ?name ?aff ?orcid ?hp WHERE {{
        ?p dblp:affiliation ?aff . ?p dblp:primaryCreatorName ?name .
        OPTIONAL {{ ?p dblp:orcid ?orcid }} OPTIONAL {{ ?p dblp:primaryHomepage ?hp }}
        FILTER({flt}) }}""")
    out: dict[str, dict] = {}
    for r in rows:
        d = out.setdefault(pid_of(r["p"]), {"pid": pid_of(r["p"]), "name": r["name"], "affiliations": set(), "orcid": "", "homepage": ""})
        d["affiliations"].add(r["aff"])
        d["orcid"] = (r.get("orcid") or d["orcid"]).rsplit("/", 1)[-1]
        d["homepage"] = r.get("hp") or d["homepage"]
    return list(out.values())


def persons_by_names(names: list[str]) -> list[dict]:
    """Persons with any creatorName exactly equal to one of `names` (batched)."""
    out = []
    names = sorted(set(n for n in names if n and '"' not in n))
    for i in range(0, len(names), 60):
        vals = " ".join(f'"{n}"' for n in names[i : i + 60])
        out += [{"query_name": r["n"], "pid": pid_of(r["p"]), "name": r["name"], "affiliation": r.get("aff", ""), "orcid": (r.get("orcid") or "").rsplit("/", 1)[-1]}
                for r in sparql(f"""SELECT ?n ?p ?name ?aff ?orcid WHERE {{
                    VALUES ?n {{ {vals} }} ?p dblp:creatorName ?n . ?p dblp:primaryCreatorName ?name .
                    OPTIONAL {{ ?p dblp:primaryAffiliation ?aff }} OPTIONAL {{ ?p dblp:orcid ?orcid }} }}""")]
    return out


def person_info(pids: list[str]) -> dict[str, dict]:
    out = {}
    pids = sorted(set(pids))
    for i in range(0, len(pids), 50):
        vals = " ".join(f"<https://dblp.org/pid/{p}>" for p in pids[i : i + 50])
        for r in sparql(f"""SELECT ?p ?name ?aff ?orcid WHERE {{ VALUES ?p {{ {vals} }} ?p dblp:primaryCreatorName ?name .
                OPTIONAL {{ ?p dblp:affiliation ?aff }} OPTIONAL {{ ?p dblp:orcid ?orcid }} }}"""):
            d = out.setdefault(pid_of(r["p"]), {"name": r["name"], "affiliations": set(), "orcids": set()})
            if r.get("aff"):
                d["affiliations"].add(r["aff"])
            if r.get("orcid"):
                d["orcids"].add(r["orcid"].rsplit("/", 1)[-1])
    return out


def _type(types: set[str], venue: str) -> str:
    if "Informal" in types or venue == "CoRR":
        return "preprint"
    if "Article" in types:
        return "journal"
    if "Inproceedings" in types:
        return "conference"
    return "other"


def prefetch(pids: list[str], since: int = 2013, batch: int = 25) -> None:
    """Fill the publication cache for many PIDs with few queries."""
    todo = sorted(set(p for p in pids if p and p not in _pub_cache))
    info = person_info(todo)
    for i in range(0, len(todo), batch):
        chunk = todo[i : i + batch]
        vals = " ".join(f"<https://dblp.org/pid/{p}>" for p in chunk)
        rows = sparql(f"""SELECT ?a ?pub ?type ?title ?year ?doi ?venue ?n WHERE {{
            VALUES ?a {{ {vals} }} ?pub dblp:authoredBy ?a . ?pub rdf:type ?type .
            ?pub dblp:yearOfPublication ?year . FILTER(?year >= "{since}"^^<http://www.w3.org/2001/XMLSchema#gYear> || STR(?year) >= "{since}")
            OPTIONAL {{ ?pub dblp:title ?title }} OPTIONAL {{ ?pub dblp:doi ?doi }} OPTIONAL {{ ?pub dblp:publishedIn ?venue }}
            OPTIONAL {{ ?pub dblp:numberOfCreators ?n }} }}""")
        recs: dict[tuple[str, str], dict] = {}
        for r in rows:
            k = (pid_of(r["a"]), r["pub"])
            d = recs.setdefault(k, {"types": set(), "dois": set(), "title": "", "year": None, "venue": "", "n": None})
            d["types"].add(r["type"].rsplit("#", 1)[-1])
            if r.get("doi"):
                d["dois"].add(normalise_doi(r["doi"]))
            d["title"] = r.get("title") or d["title"]
            d["venue"] = r.get("venue") or d["venue"]
            d["year"] = int(str(r["year"])[:4])
            d["n"] = int(r["n"]) if r.get("n") else d["n"]
        for p in chunk:
            pi = info.get(p, {})
            _pub_cache[p] = {"pid": p, "name": pi.get("name", ""), "affiliations": sorted(pi.get("affiliations", [])),
                             "orcids": sorted(pi.get("orcids", [])), "records": []}
        for (p, pub), d in recs.items():
            key = pub.split("/rec/", 1)[-1]
            typ = _type(d["types"], d["venue"])
            _pub_cache[p]["records"].append({
                "dblp_key": key, "dblp_type": typ, "year": d["year"], "title": (d["title"] or "").rstrip("."),
                "venue": d["venue"], "venue_key": "/".join(key.split("/")[:2]), "dois": sorted(x for x in d["dois"] if x),
                "n_authors": d["n"], "authors": [], "author_pids": [],
            })


def person_publications(pid: str) -> dict:
    """{'pid','name','affiliations','orcids','records'}; records since 2013 (enough for the
    2016–2026 window with a pre-joining margin)."""
    if pid not in _pub_cache:
        prefetch([pid])
    return _pub_cache[pid]
