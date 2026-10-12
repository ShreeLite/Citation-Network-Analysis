"""Cross-source record clustering (DOI first, then fuzzy title + year + shared faculty) and
arXiv-preprint collapse. Pure functions over plain dicts so they are unit-testable.

A record is a dict with at least:
  rid (unique), source, doi, title, year, is_preprint (bool), faculty_ids (set[str])
"""
from __future__ import annotations

from collections import defaultdict

from rapidfuzz import fuzz

from .titles import is_arxiv_doi, normalise_title


class UnionFind:
    def __init__(self):
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


def title_match(a: str, b: str, threshold: float) -> bool:
    """Normalised-title similarity; guards against a short title matching a long one."""
    if not a or not b:
        return False
    if a == b:
        return True
    la, lb = len(a), len(b)
    if min(la, lb) / max(la, lb) < 0.8:
        return False
    return fuzz.ratio(a, b) >= threshold


def cluster(records: list[dict], threshold: float = 93, preprint_year_gap: int = 2) -> dict[str, str]:
    """Return {rid: cluster_id}."""
    uf = UnionFind()
    for r in records:
        uf.find(r["rid"])
        r["_nt"] = r.get("_nt") or normalise_title(r.get("title"))

    # 1. same DOI (arXiv DOIs only join other arXiv records with the same DOI)
    by_doi = defaultdict(list)
    for r in records:
        if r.get("doi"):
            by_doi[r["doi"]].append(r["rid"])
    for rids in by_doi.values():
        for x in rids[1:]:
            uf.union(rids[0], x)

    # 2. fuzzy title + year window + at least one shared faculty member (blocked per faculty)
    by_fac = defaultdict(list)
    for r in records:
        for f in r.get("faculty_ids") or ():
            by_fac[f].append(r)
    for recs in by_fac.values():
        recs = sorted(recs, key=lambda r: r["_nt"])
        n = len(recs)
        for i in range(n):
            a = recs[i]
            for j in range(i + 1, n):
                b = recs[j]
                if a["_nt"][:12] != b["_nt"][:12] and fuzz.ratio(a["_nt"][:30], b["_nt"][:30]) < 70:
                    # sorted by title: once prefixes diverge strongly, later ones diverge too
                    if a["_nt"][:3] != b["_nt"][:3]:
                        break
                    continue
                gap = preprint_year_gap if (a.get("is_preprint") or b.get("is_preprint")) else 1
                if a.get("year") and b.get("year") and abs(a["year"] - b["year"]) > gap:
                    continue
                # two different non-arXiv DOIs = two different works (e.g. conf + journal version)
                da, db = a.get("doi"), b.get("doi")
                if da and db and da != db and not is_arxiv_doi(da) and not is_arxiv_doi(db):
                    continue
                if title_match(a["_nt"], b["_nt"], threshold):
                    uf.union(a["rid"], b["rid"])
    return {r["rid"]: uf.find(r["rid"]) for r in records}


def tune_threshold(records: list[dict], thresholds=(85, 88, 90, 92, 93, 95, 97)) -> list[dict]:
    """Precision/recall of the fuzzy title rule against DOI ground truth: pairs of records from
    *different sources* sharing a faculty member, labelled positive when their DOIs are equal."""
    by_fac = defaultdict(list)
    for r in records:
        if r.get("doi") and not is_arxiv_doi(r["doi"]):
            for f in r.get("faculty_ids") or ():
                by_fac[f].append(r)
    pairs = []
    for recs in by_fac.values():
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                a, b = recs[i], recs[j]
                if a["source"] == b["source"]:
                    continue
                na, nb = normalise_title(a["title"]), normalise_title(b["title"])
                if not na or not nb:
                    continue
                if fuzz.ratio(na[:20], nb[:20]) < 60 and a["doi"] != b["doi"]:
                    continue  # obviously different; keep pair count manageable
                yr_ok = not (a.get("year") and b.get("year") and abs(a["year"] - b["year"]) > 1)
                pairs.append((a["doi"] == b["doi"], na, nb, yr_ok))
    out = []
    for t in thresholds:
        tp = sum(1 for y, a, b, ok in pairs if y and ok and title_match(a, b, t))
        fp = sum(1 for y, a, b, ok in pairs if not y and ok and title_match(a, b, t))
        fn = sum(1 for y, a, b, ok in pairs if y and not (ok and title_match(a, b, t)))
        out.append({"threshold": t, "tp": tp, "fp": fp, "fn": fn,
                    "precision": round(tp / (tp + fp), 4) if tp + fp else None,
                    "recall": round(tp / (tp + fn), 4) if tp + fn else None})
    return out
