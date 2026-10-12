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


def _token_match(a: str, b: str) -> str | None:
    """'exact' | 'fuzzy' (spelling variant / prefix) | 'initial' | None."""
    if a == b:
        return "exact"
    if len(a) == 1 or len(b) == 1:
        return "initial" if a[0] == b[0] else None
    if fuzz.ratio(a, b) >= 85 or (min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a))):
        return "fuzzy"  # Srinivas/Srinivasa, Kamal/Kamalakar
    return None


def name_similarity(a: str, b: str) -> float:
    """0..1, order-insensitive and initial-aware.

    Rules: every token of the shorter name must pair with a distinct token of the longer one;
    when both names have ≥ 2 full (non-initial) tokens, at least 2 full tokens must match
    (so 'Prasad Krishnan' ≠ 'Krishna Reddy P'); unmatched full tokens in the longer name
    (dropped middle names) cost 0.1 each; spelling-variant matches cost 0.05 each."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    if ta == tb or sorted(ta) == sorted(tb):
        return 1.0
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    used = [False] * len(long_)
    kinds = []
    half_initial = 0
    # full tokens first (longest first) so initials don't steal their partners
    for t in sorted(short, key=len, reverse=True):
        best, best_kind = None, None
        for i, u in enumerate(long_):
            if used[i]:
                continue
            k = _token_match(t, u)
            if k and (best is None or ["initial", "fuzzy", "exact"].index(k) > ["initial", "fuzzy", "exact"].index(best_kind)):
                best, best_kind = i, k
        if best is None:
            return 0.0 if not kinds else round(0.5 * len(kinds) / len(short), 3)
        used[best] = True
        kinds.append(best_kind)
        if best_kind == "initial" and (len(t) > 1) != (len(long_[best]) > 1):
            half_initial += 1  # full given name on one side, only its initial on the other
    full_short = sum(1 for t in short if len(t) > 1)
    full_long = sum(1 for t in long_ if len(t) > 1)
    full_matches = sum(1 for k, t in zip(kinds, sorted(short, key=len, reverse=True)) if k in ("exact", "fuzzy") and len(t) > 1)
    if full_matches == 0:
        return 0.0
    if full_short >= 2 and full_long >= 2 and full_matches < 2:
        return 0.6
    extra_full = sum(1 for i, u in enumerate(long_) if not used[i] and len(u) > 1)
    score = 1.0 - 0.1 * extra_full - 0.05 * kinds.count("fuzzy")
    # one side spells the given name in full, the other only has its initial, and only the
    # surname matches in full: 'A. Kumar' fits every A-named Kumar, so it is weak evidence
    if full_matches == 1 and half_initial >= 1:
        score = min(score, 0.8)
    return round(max(0.0, min(1.0, score)), 3)


def surname_like(name: str) -> str:
    """Token most likely to be shared across variants (longest full token)."""
    toks = [t for t in tokens(name) if len(t) > 1]
    return max(toks, key=len) if toks else ""
