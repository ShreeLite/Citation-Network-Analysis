"""Proxy journal quartile from OpenAlex, used ONLY when Scimago SJR files are unavailable.

For each OpenAlex field, draw a seeded random sample of journals with that field among their
topics (≥ 50 works), keep those whose *top* topic is in the field, and take the quartile
thresholds of their 2-year mean citedness (an impact-factor-like measure). A journal's proxy
quartile is its position in its own top field. Reported in a separate column
(`quartile_proxy_openalex`) and always labelled as a proxy; the official `quartile` column is
SJR-only.
"""
from __future__ import annotations

import logging

import numpy as np

from .sources import oa_get, oa_lookup, short_id

log = logging.getLogger("quartile_proxy")


def _top_field(src: dict) -> str | None:
    t = (src.get("topics") or [])
    return short_id(((t[0].get("field") or {}).get("id"))) if t else None


def field_thresholds(field_id: str, n_pages: int = 20) -> tuple[float, float, float] | None:
    vals = []
    for page in range(1, n_pages + 1):
        res = oa_get("sources", filter=f"type:journal,topics.field.id:{field_id},works_count:>500", sample=2000, seed=42,
                     select="id,summary_stats,topics", page=page, **{"per-page": 100})
        rs = res.get("results", [])
        for s in rs:
            st = s.get("summary_stats") or {}
            # SJR ranks a curated (Scopus-indexed) population; OpenAlex also lists thousands of tiny,
            # uncited journals that would drag thresholds down. Calibrate on established journals.
            if _top_field(s) == field_id and (st.get("2yr_mean_citedness") or 0) > 0 and (st.get("h_index") or 0) >= 10:
                vals.append(st["2yr_mean_citedness"])
        if len(rs) < 100:
            break
    if len(vals) < 50:
        return None
    q75, q50, q25 = np.quantile(vals, [0.75, 0.5, 0.25])
    log.info("field %s: %d journals sampled; Q1 ≥ %.2f, Q2 ≥ %.2f, Q3 ≥ %.2f", field_id, len(vals), q75, q50, q25)
    return float(q75), float(q50), float(q25)


def proxy_quartiles(source_ids: list[str]) -> dict[str, dict]:
    """{source_id: {quartile_proxy_openalex, field, citedness}} for journal sources."""
    srcs = {short_id(s["id"]): s for s in oa_lookup("sources", "openalex_id", source_ids, select="id,display_name,type,summary_stats,topics")}
    fields = {f for s in srcs.values() if s.get("type") == "journal" for f in [_top_field(s)] if f}
    thr = {f: field_thresholds(f) for f in sorted(fields)}
    out = {}
    for sid, s in srcs.items():
        f = _top_field(s)
        v = (s.get("summary_stats") or {}).get("2yr_mean_citedness")
        if s.get("type") != "journal" or not f or thr.get(f) is None or v is None:
            continue
        q75, q50, q25 = thr[f]
        q = "Q1" if v >= q75 else "Q2" if v >= q50 else "Q3" if v >= q25 else "Q4"
        out[sid] = {"quartile_proxy_openalex": q, "proxy_field": f, "two_yr_mean_citedness": v}
    return out
