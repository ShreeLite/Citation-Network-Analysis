"""Venue normalisation: long proceedings names -> canonical venue + acronym."""
from __future__ import annotations

import re

from unidecode import unidecode

ORDINAL = r"\b\d+(?:st|nd|rd|th)\b"
NOISE_PHRASES = [
    r"proceedings of (?:the )?", r"\bproc\.?\s", r"\bin\s*:\s*", r"companion (?:volume|proceedings) of (?:the )?",
    r"\b(?:ieee|acm|ieee/cvf|cvf|ieee-cvf|usenix|aaai|siam|springer|elsevier)\b/?", r"\bannual\b", r"\bworkshops?\b(?= of| on)",
    r"\bvolume\s+\d+\b", r"\bvol\.?\s*\d+\b", r"\bpart\s+[ivx\d]+\b",
]
# Acronyms that DBLP venue keys spell differently from common usage
DBLP_KEY_ACRONYM = {
    "nips": "NeurIPS", "iclr": "ICLR", "icml": "ICML", "cvpr": "CVPR", "iccv": "ICCV", "eccv": "ECCV",
    "acl": "ACL", "emnlp": "EMNLP", "naacl": "NAACL", "coling": "COLING", "eacl": "EACL", "aaai": "AAAI",
    "ijcai": "IJCAI", "kdd": "KDD", "www": "WWW", "sigir": "SIGIR", "wsdm": "WSDM", "cikm": "CIKM",
    "icassp": "ICASSP", "interspeech": "INTERSPEECH", "mm": "ACM MM", "chi": "CHI", "icse": "ICSE",
    "sigsoft": "FSE", "kbse": "ASE", "icra": "ICRA", "iros": "IROS", "rss": "RSS", "wacv": "WACV",
    "bmvc": "BMVC", "icvgip": "ICVGIP", "miccai": "MICCAI", "isbi": "ISBI", "icpr": "ICPR", "icdar": "ICDAR",
    "ccs": "CCS", "sp": "S&P", "uss": "USENIX Security", "ndss": "NDSS", "stoc": "STOC", "focs": "FOCS",
    "soda": "SODA", "icalp": "ICALP", "fsttcs": "FSTTCS", "sigmod": "SIGMOD", "vldb": "VLDB", "pvldb": "VLDB",
    "icde": "ICDE", "sigcomm": "SIGCOMM", "nsdi": "NSDI", "infocom": "INFOCOM", "mobicom": "MobiCom",
    "comsnets": "COMSNETS", "icwsm": "ICWSM", "cscw": "CSCW", "recsys": "RecSys", "ecir": "ECIR",
    "ijcnlp": "IJCNLP", "conll": "CoNLL", "lrec": "LREC", "icon": "ICON", "dac": "DAC", "date": "DATE",
    "iccad": "ICCAD", "vlsid": "VLSID", "iscas": "ISCAS", "globecom": "GLOBECOM", "icc": "ICC", "vtc": "VTC",
    "wcnc": "WCNC", "spcom": "SPCOM", "ncc": "NCC", "eusipco": "EUSIPCO", "icip": "ICIP", "icme": "ICME",
    "uai": "UAI", "aistats": "AISTATS", "colt": "COLT", "ecai": "ECAI", "aamas": "AAMAS", "pakdd": "PAKDD",
    "sdm": "SDM", "icdm": "ICDM", "asonam": "ASONAM", "hicss": "HICSS", "comad": "CODS-COMAD",
}


def strip_years(s: str) -> str:
    s = re.sub(r"(?<!\d)(?:19|20)\d{2}(?!\d)", " ", s)
    s = re.sub(r"\b'\d{2}\b", " ", s)
    return s


def venue_key(name: str | None) -> str:
    """Lowercased, year/ordinal/publisher-free key used to cluster name variants."""
    if not name:
        return ""
    s = unidecode(name).lower()
    s = re.sub(r"\([^)]*\)", " ", s)  # parenthesised acronyms / locations
    s = strip_years(s)
    s = re.sub(ORDINAL, " ", s)
    s = re.sub(r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\w+teenth|twenty\w*|thirty\w*|fort\w*|fift\w*)\b", " ", s)
    for p in NOISE_PHRASES:
        s = re.sub(p, " ", s)
    s = re.sub(r",.*$", "", s) if len(s) > 60 else s  # drop trailing ", city, country" on long names
    s = re.sub(r"[^a-z0-9& ]", " ", s)
    s = re.sub(r"\b(?:the|of|on|and|in|for)\b", " ", s)
    return " ".join(s.split())


def extract_acronym(name: str | None) -> str:
    if not name:
        return ""
    m = re.search(r"\(([A-Z][A-Za-z@&\-]{1,14})(?:[\s'’-]*\d{2,4})?\)", name)
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z][A-Z@&\-]{2,12})\s*['’]?\s*(?:19|20)?\d{2}\b", name)
    if m and m.group(1) not in ("IEEE", "ACM", "CVF", "USENIX", "SIAM"):
        return m.group(1)
    return ""


def dblp_acronym(venue_key_: str | None) -> str:
    """'conf/cvpr' -> 'CVPR'; journals/* -> '' (journal names are used as-is)."""
    if not venue_key_ or not venue_key_.startswith("conf/"):
        return ""
    k = venue_key_.split("/", 1)[1]
    return DBLP_KEY_ACRONYM.get(k, k.upper())
