"""Fetch and parse a DBLP person record (https://dblp.org/pid/<pid>.xml)."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .sources import dblp
from .titles import normalise_doi

RECORD_TAGS = ("article", "inproceedings", "proceedings", "book", "incollection", "phdthesis", "mastersthesis", "data")


def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def person_publications(pid: str) -> dict:
    """{'name':..., 'pid':..., 'affiliations': [...], 'orcids': [...], 'records': [...]}.
    Each record: key, type (journal/conference/preprint/other), year, title, venue, dois, ees, authors."""
    xml = dblp().get(f"https://dblp.org/pid/{pid}.xml", ext="xml")
    root = ET.fromstring(xml)
    person = root.find("person")
    affs = [_text(n) for n in person.findall("note") if n.get("type") == "affiliation"] if person is not None else []
    orcids = []
    if person is not None:
        for a in person.findall("author"):
            if a.get("orcid"):
                orcids.append(a.get("orcid"))
    recs = []
    for r in root.findall("r"):
        el = next((c for c in r if c.tag in RECORD_TAGS), None)
        if el is None:
            continue
        key = el.get("key", "")
        ees = [_text(e) for e in el.findall("ee")]
        dois = sorted({normalise_doi(e) for e in ees if "doi.org/" in e})
        venue = _text(el.find("journal")) or _text(el.find("booktitle"))
        if key.startswith("journals/corr") or venue == "CoRR":
            typ = "preprint"
        elif key.startswith("journals/"):
            typ = "journal"
        elif key.startswith("conf/"):
            typ = "conference"
        else:
            typ = "other"
        year = _text(el.find("year"))
        recs.append({
            "dblp_key": key,
            "dblp_type": typ,
            "publtype": el.get("publtype", ""),
            "year": int(year) if year.isdigit() else None,
            "title": re.sub(r"\.$", "", _text(el.find("title"))),
            "venue": venue,
            "venue_key": "/".join(key.split("/")[:2]),
            "volume": _text(el.find("volume")),
            "pages": _text(el.find("pages")),
            "dois": dois,
            "ees": ees,
            "authors": [_text(a) for a in el.findall("author")],
            "author_pids": [a.get("pid", "") for a in el.findall("author")],
        })
    return {
        "pid": pid,
        "name": person.findtext("author") if person is not None else "",
        "affiliations": affs,
        "orcids": orcids,
        "records": recs,
    }
