"""Title and DOI normalisation for cross-source deduplication."""
from __future__ import annotations

import html
import re

from unidecode import unidecode

STOPWORDS = {
    "a", "an", "the", "of", "for", "and", "in", "on", "to", "with", "by", "via", "using",
    "from", "at", "is", "are", "towards", "toward", "its", "into", "as", "or",
}


def normalise_title(title: str | None) -> str:
    if not title:
        return ""
    s = html.unescape(title)
    s = re.sub(r"<[^>]+>", " ", s)          # <i>, <sub> from Crossref/OpenAlex
    s = re.sub(r"\$[^$]*\$", " ", s)        # inline LaTeX from DBLP/arXiv
    s = unidecode(s).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    toks = [t for t in s.split() if t not in STOPWORDS]
    return " ".join(toks)


def normalise_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = d.removeprefix("doi:").strip()
    return d or None


ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.", re.I)


def is_arxiv_doi(doi: str | None) -> bool:
    return bool(doi and ARXIV_DOI.match(doi))
