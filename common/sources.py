"""Configured fetchers for each external source, plus OpenAlex paging helpers."""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Iterator

from .config import cfg, secret
from .http import Fetcher

log = logging.getLogger("sources")

OPENALEX = "https://api.openalex.org"
OA_MAX_PER_PAGE = 100   # API maximum as of Aug 2026 (was 200)
OA_MAX_OR = 100         # max OR values per filter


@lru_cache(maxsize=None)
def openalex() -> Fetcher:
    key = secret("OPENALEX_API_KEY", required=True)
    return Fetcher("openalex", default_params={"api_key": key, "mailto": cfg()["contact_email"]})


@lru_cache(maxsize=None)
def crossref() -> Fetcher:
    return Fetcher("crossref", default_params={"mailto": cfg()["contact_email"]})


@lru_cache(maxsize=None)
def dblp() -> Fetcher:
    return Fetcher("dblp")


@lru_cache(maxsize=None)
def s2() -> Fetcher:
    key = secret("S2_API_KEY")
    return Fetcher("s2", headers={"x-api-key": key} if key else None)


@lru_cache(maxsize=None)
def ror() -> Fetcher:
    return Fetcher("ror")


@lru_cache(maxsize=None)
def wayback() -> Fetcher:
    return Fetcher("wayback", timeout=90)


@lru_cache(maxsize=None)
def web() -> Fetcher:
    """Institute websites and faculty homepages: robots.txt obeyed, polite delay."""
    return Fetcher("web", obey_robots=True, timeout=30, max_attempts=3, max_wait=15, negative_cache=True)


def oa_get(path: str, **params) -> dict:
    return openalex().get(f"{OPENALEX}/{path.lstrip('/')}", params=params)


def oa_paginate(path: str, filter: str, select: str | None = None, **extra) -> Iterator[dict]:
    """Cursor-paginate an OpenAlex list endpoint. Each page is cached individually, keyed by
    its cursor, so an interrupted pull resumes from the cache."""
    cursor = "*"
    while cursor:
        params = {"filter": filter, "per-page": OA_MAX_PER_PAGE, "cursor": cursor, **extra}
        if select:
            params["select"] = select
        page = oa_get(path, **params)
        yield from page.get("results", [])
        cursor = page.get("meta", {}).get("next_cursor")
        if not page.get("results"):
            break


_budget_gone = False


def oa_singleton(entity: str, ident: str, select: str | None = None) -> dict | None:
    """GET /<entity>/<ident> (ident may be 'W123', 'doi:10.x/y', 'orcid:0000-...').
    Singleton requests cost 0 credits. Returns None on 404."""
    from .http import PermanentHTTPError
    try:
        return oa_get(f"{entity}/{ident}", **({"select": select} if select else {}))
    except PermanentHTTPError as e:
        if e.status == 404:
            return None
        raise


def oa_lookup(entity: str, filter_key: str, values: list[str], select: str | None = None,
              batch: int = OA_MAX_OR, singleton_prefix: str = "") -> list[dict]:
    """Fetch many entities by an ID-like filter. Uses OR-batched list calls (1 credit per
    `batch` values); once the daily budget is exhausted, continues with free singleton calls
    (`/<entity>/<singleton_prefix><value>`) so the step still completes."""
    from .http import BudgetExhausted, PermanentHTTPError
    global _budget_gone
    allv = sorted(set(v for v in values if v))
    # values containing filter syntax (',' '|' '+' etc.) cannot go into an OR filter
    bad = [v for v in allv if re.search(r"[,|+&<>\s]", v)]
    vals = [v for v in allv if v not in set(bad)]
    out, single = [], list(bad)
    i = 0
    while i < len(vals) and not _budget_gone:
        ch = vals[i : i + batch]
        try:
            res = oa_get(entity, filter=f"{filter_key}:" + "|".join(ch), **{"per-page": OA_MAX_PER_PAGE},
                         **({"select": select} if select else {}))
            out += res.get("results", [])
        except BudgetExhausted:
            log.warning("OpenAlex list budget exhausted; switching to free singleton lookups")
            _budget_gone = True
            break
        except PermanentHTTPError as e:
            if e.status != 400:
                raise
            single += ch  # one malformed value spoils the batch: look these up one by one
        i += batch
    single += vals[i:]
    for v in single:
        try:
            r = oa_singleton(entity, f"{singleton_prefix}{v}", select)
        except PermanentHTTPError as e:
            log.info("singleton %s %s failed: %s", entity, v, e)
            continue
        if r:
            out.append(r)
    return out


def chunks(seq, n: int):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def short_id(oa_id: str | None) -> str | None:
    """'https://openalex.org/A123' -> 'A123'."""
    if not oa_id:
        return None
    return oa_id.rstrip("/").rsplit("/", 1)[-1]
