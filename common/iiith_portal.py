"""IIIT-H official publications portal (iiit.ac.in/publications/) — institute-reported records
with type (from BibTeX entry type), CORE rank as recorded by the institute, DOI link, authors.

The portal pages via a read-only POST (page=N, ajax=1) returning JSON {cards, pagination,
countHTML}. Each page is cached, so the full crawl resumes where it stopped.
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from tqdm import tqdm

from .sources import web
from .titles import normalise_doi

log = logging.getLogger("iiith_portal")
URL = "https://iiit.ac.in/publications/index.php"
FORM = {"stitle": "", "sauthor": "", "sconfname": "", "sacronym": "", "spyear": "", "sconftype": ""}


def _page(n: int) -> dict:
    return web().get(URL, ext="json", data={"page": str(n), "ajax": "1", **FORM},
                     headers={"X-Requested-With": "XMLHttpRequest"})


def parse_cards(html: str) -> list[dict]:
    s = BeautifulSoup(html, "lxml")
    out = []
    for card in s.select("div.card"):
        t = card.select_one(".publication-title")
        if not t:
            continue
        about = card.select_one(".about-publication")
        about_txt = " ".join(about.get_text(" ").split()) if about else ""
        parts = [p.strip() for p in about_txt.split(",") if p.strip()]
        year = next((int(p) for p in reversed(parts) if re.fullmatch(r"(19|20)\d{2}", p)), None)
        venue = parts[0] if parts else ""
        acronym = parts[1] if len(parts) > 2 else ""
        core = ""
        for b in card.select(".badge"):
            if m := re.search(r"Core Rank\s*:\s*(\S+)", b.get_text()):
                core = m.group(1) if m.group(1) != "-" else ""
        bib = card.select_one(".divbox")
        bibtxt = bib.get_text(" ") if bib else ""
        entry = (re.match(r"\s*@(\w+)", bibtxt) or [None, ""])[1].lower()
        doi_link = ""
        for a in card.select(".links a[href]"):
            if "DOI" in a.get_text():
                doi_link = a["href"]
        doi = normalise_doi(doi_link) if "doi.org/" in doi_link else None
        if not doi and (m := re.search(r"(10\.\d{4,9}/[^\s\"'<>]+)", doi_link)):
            doi = normalise_doi(m.group(1))
        authors = card.select_one(".author")
        out.append({
            "title": " ".join(t.get_text(" ").split()),
            "authors": [a.strip() for a in (authors.get_text(" ") if authors else "").split(",") if a.strip()],
            "venue": venue,
            "acronym": acronym,
            "year": year,
            "core_rank_portal": core,
            "bibtex_entry": entry,
            "doi": doi,
            "link": doi_link,
        })
    return out


def journal_titles() -> set[str]:
    """Normalised titles the portal itself classifies as 'Journal Paper' (its BibTeX entry type
    is @inproceedings for everything, so the filter is the only reliable type signal)."""
    from .titles import normalise_title
    data = {"page": "1", "ajax": "1", **FORM, "sconftype": "Journal Paper"}
    first = web().get(URL, ext="json", data=data, headers={"X-Requested-With": "XMLHttpRequest"})
    m = re.search(r"\((\s*\d+\s*)\)", re.sub(r"<[^>]+>", " ", first.get("countHTML", "")))
    n_pages = (int(m.group(1)) + 9) // 10 if m else 1
    titles = {normalise_title(c["title"]) for c in parse_cards(first.get("cards", ""))}
    for n in tqdm(range(2, n_pages + 1), desc="IIIT-H portal journal pages"):
        try:
            page = web().get(URL, ext="json", data={**data, "page": str(n)}, headers={"X-Requested-With": "XMLHttpRequest"})
            titles |= {normalise_title(c["title"]) for c in parse_cards(page.get("cards", ""))}
        except Exception as e:
            log.warning("portal journal page %d failed: %s", n, e)
    return titles


def all_publications() -> list[dict]:
    first = _page(1)
    m = re.search(r"Total Publications:\s*</?[^>]*>?\s*(\d+)", first.get("countHTML", "")) or \
        re.search(r"(\d+)", re.sub(r"<[^>]+>", " ", first.get("countHTML", "")))
    total = int(m.group(1)) if m else 0
    pages = re.findall(r"data-page='(\d+)'", first.get("pagination", ""))
    n_pages = max([int(p) for p in pages] + [(total + 9) // 10, 1])
    recs = parse_cards(first.get("cards", ""))
    for n in tqdm(range(2, n_pages + 1), desc="IIIT-H portal pages"):
        try:
            recs += parse_cards(_page(n).get("cards", ""))
        except Exception as e:
            log.warning("portal page %d failed: %s", n, e)
    jt = journal_titles()
    from .titles import normalise_title
    for rec in recs:
        rec["portal_type"] = "journal" if normalise_title(rec["title"]) in jt else ""
    log.info("IIIT-H portal: %d records (reported total %d), %d typed journal", len(recs), total, sum(r["portal_type"] == "journal" for r in recs))
    return recs
