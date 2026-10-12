"""Configured fetchers for each external source, plus OpenAlex paging helpers."""
from __future__ import annotations

import logging
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
    return Fetcher("web", obey_robots=True, timeout=45)


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


def chunks(seq, n: int):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def short_id(oa_id: str | None) -> str | None:
    """'https://openalex.org/A123' -> 'A123'."""
    if not oa_id:
        return None
    return oa_id.rstrip("/").rsplit("/", 1)[-1]
