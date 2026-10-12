"""Person-name normalisation and fuzzy matching tuned for Indian academic names.

Handles: honorifics, initials ("P. J. Narayanan" vs "Narayanan P J"), reordered South-Indian
names (initial-first, given-name-last), expansions like "K." -> "Kumar", dropped middle
names, diacritics and hyphenation.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz
from unidecode import unidecode

HONORIFICS = {
    "dr", "prof", "professor", "mr", "mrs", "ms", "shri", "smt", "sri", "er", "phd",
    "assistant", "associate", "adjunct", "visiting", "emeritus", "head", "hod",
}


def normalise(name: str) -> str:
    s = unidecode(name or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = s.replace("-", " ").replace("'", "")
    s = re.sub(r"[^a-z\s.]", " ", s)
    s = s.replace(".", " ")
    toks = [t for t in s.split() if t not in HONORIFICS]
    return " ".join(toks)


def tokens(name: str) -> list[str]:
    return normalise(name).split()


def initials_key(name: str) -> tuple[str, frozenset[str]]:
    """(longest token, set of first letters of the others). Order-independent so
    'Narayanan P J' and 'P J Narayanan' collide."""
    toks = tokens(name)
    if not toks:
        return "", frozenset()
    longest = max(toks, key=len)
    rest = list(toks)
    rest.remove(longest)
    return longest, frozenset(t[0] for t in rest)


def _token_compatible(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) == 1 or len(b) == 1:  # initial vs full token
        return a[0] == b[0]
    return fuzz.ratio(a, b) >= 85  # spelling variants: Srinivas/Srinivasa, Ponnurangam/Ponnurangum


def name_similarity(a: str, b: str) -> float:
    """0..1. Order-insensitive, initial-aware. 1.0 = every token of the shorter name is
    compatible with a distinct token of the longer one and at least one full (non-initial)
    token matches exactly-ish."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    if ta == tb:
        return 1.0
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    used = [False] * len(long_)
    matched, full_matched = 0, 0
    # full tokens first so initials don't steal their partners
    for t in sorted(short, key=len, reverse=True):
        best = None
        for i, u in enumerate(long_):
            if not used[i] and _token_compatible(t, u):
                if best is None or (len(u) > 1) == (len(t) > 1):
                    best = i
                    if (len(u) > 1) == (len(t) > 1):
                        break
        if best is not None:
            used[best] = True
            matched += 1
            if len(t) > 1 and len(long_[best]) > 1:
                full_matched += 1
    if full_matched == 0:
        return 0.0
    coverage = matched / len(short)
    # penalise unmatched full tokens in the longer name lightly (dropped middle names are common)
    extra_full = sum(1 for i, u in enumerate(long_) if not used[i] and len(u) > 1)
    score = coverage - 0.08 * extra_full
    # fall back to plain fuzzy on the joined string for transliteration differences
    plain = fuzz.token_sort_ratio(" ".join(ta), " ".join(tb)) / 100
    return max(0.0, min(1.0, max(score, plain if coverage == 1 else plain * 0.9)))


def surname_like(name: str) -> str:
    """Token most likely to be shared across variants (longest full token)."""
    toks = [t for t in tokens(name) if len(t) > 1]
    return max(toks, key=len) if toks else ""
