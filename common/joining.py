"""Extract the year a faculty member joined IIIT-H / IIIT-D from free text (bio, homepage, CV).

Returns (year, confidence, evidence_snippet). Confidence:
  0.9  explicit "joined IIIT ... in 2017" / "at IIIT ... since 2017"
  0.8  CV-style range "2017 – present ... Assistant Professor ... IIIT"
  0.6  "faculty member/professor at IIIT ... since 2017" with the institute nearby but looser wording
Ambiguous or conflicting evidence is returned with the lowest confidence of the candidates,
and the caller sends anything < 0.8 to the review file.
"""
from __future__ import annotations

import re

YEAR = r"((?:19|20)\d{2})"

INST_PAT = {
    "IIIT-H": r"(?:IIIT[\s-]?H(?:yderabad)?|IIITH|International Institute of Information Technology,?\s*Hyderabad|IIIT,?\s*Hyderabad)",
    "IIIT-D": r"(?:IIIT[\s-]?D(?:elhi)?|IIITD|Indraprastha Institute of Information Technology,?\s*(?:Delhi)?|IIIT,?\s*Delhi)",
}
GENERIC_INST = r"(?:the institute|the institution|IIIT)"

MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
PRESENT = r"(?:present|now|current(?:ly)?|till\s+date|to\s+date|date|ongoing)"
DASH = r"\s*(?:-|–|—|to|till)\s*"


def _patterns(inst: str) -> list[tuple[re.Pattern, float]]:
    I = INST_PAT[inst]
    return [
        # "joined IIIT-Delhi in 2017", "joined IIIT Hyderabad as Assistant Professor in July 2016"
        (re.compile(rf"join(?:ed|ing)\s+(?:the\s+)?(?:faculty\s+(?:of|at)\s+)?{I}[^.\n]{{0,80}}?(?:in|since|on)\s+(?:{MONTH}\s*,?\s*)?{YEAR}", re.I), 0.9),
        # "joined in 2017" with institute mentioned within the same sentence before
        (re.compile(rf"{I}[^.\n]{{0,120}}?\bjoin(?:ed|ing)\b[^.\n]{{0,30}}?(?:in|since)\s+(?:{MONTH}\s*,?\s*)?{YEAR}", re.I), 0.85),
        # "at IIIT-Delhi since 2017" / "with IIIT Hyderabad since 2016"
        (re.compile(rf"(?:at|with|in)\s+{I}[^.\n]{{0,60}}?\bsince\s+(?:{MONTH}\s*,?\s*)?{YEAR}", re.I), 0.9),
        # "Professor ... since 2017 at IIIT"
        (re.compile(rf"\bsince\s+(?:{MONTH}\s*,?\s*)?{YEAR}[^.\n]{{0,40}}?(?:at|with|in)\s+{I}", re.I), 0.85),
        # CV line: "2017 – present  Assistant Professor, IIIT-Delhi"  (range then institute)
        (re.compile(rf"(?:{MONTH}\s*,?\s*)?{YEAR}{DASH}{PRESENT}[^\n]{{0,120}}?{I}", re.I), 0.8),
        # CV line: "Assistant Professor, IIIT-Delhi   2017 – present"
        (re.compile(rf"{I}[^\n]{{0,120}}?(?:{MONTH}\s*,?\s*)?{YEAR}{DASH}{PRESENT}", re.I), 0.8),
        # "Associate Professor at IIIT since 2017" without full institute name
        (re.compile(rf"(?:professor|faculty)[^.\n]{{0,40}}?{GENERIC_INST}[^.\n]{{0,40}}?since\s+{YEAR}", re.I), 0.6),
    ]


def extract_joining_year(text: str, inst: str, min_year: int = 1998, max_year: int = 2026):
    """Return (year, confidence, evidence) or (None, 0.0, None)."""
    if not text:
        return None, 0.0, None
    text = re.sub(r"[ \t\xa0]+", " ", text)
    hits: list[tuple[int, float, str]] = []
    for pat, conf in _patterns(inst):
        for m in pat.finditer(text):
            years = [int(g) for g in m.groups() if g and re.fullmatch(r"(?:19|20)\d{2}", g)]
            if not years:
                continue
            y = years[0]
            if min_year <= y <= max_year:
                s, e = max(0, m.start() - 40), min(len(text), m.end() + 40)
                hits.append((y, conf, text[s:e].replace("\n", " ").strip()))
    if not hits:
        return None, 0.0, None
    years = {h[0] for h in hits}
    best = max(hits, key=lambda h: h[1])
    if len(years) > 1:
        # Conflicting years (e.g. rejoined, or postdoc then faculty): earliest high-confidence
        # one is the usual answer, but flag it by lowering confidence.
        strong = [h for h in hits if h[1] >= 0.8] or hits
        y = min(h[0] for h in strong)
        ev = " | ".join(sorted({h[2] for h in hits}))[:400]
        return y, min(0.6, best[1]), f"CONFLICT {sorted(years)}: {ev}"
    return best[0], best[1], best[2]
