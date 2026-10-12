"""NIRF data-capturing-system (DCS) files: per-faculty tables with designation, joining date,
leaving date and association type, submitted by each institute every year.

Files come from nirfindia.org (no robots.txt; public) — located by finding the institute's row
on each year's ranking page — and, for IIIT-D, its own site as a fallback.
"""
from __future__ import annotations

import io
import logging
import re

from bs4 import BeautifulSoup
from pypdf import PdfReader

from .http import PermanentHTTPError
from .sources import web

log = logging.getLogger("nirf")

RANK_PAGES = ["EngineeringRanking", "OverallRanking", "UniversityRanking"]
NAME_PAT = {
    "IIIT-H": re.compile(r"International Institute of Information Technology,?\s*Hyderabad", re.I),
    "IIIT-D": re.compile(r"Indraprastha Institute of Information Technology", re.I),
}
DESIG = r"(Assistant Professor|Associate Professor|Professor|Lecturer|Dean / Principal / Director / Vice Chancellor|Other)"
ROW = re.compile(
    rf"^(\d+) (.+?)(?: \d{{2}})? {DESIG} (Male|Female|Transgender|Other) (\S+(?: \S+)?) (\d+) (Yes|No) (\d{{2}}-\d{{2}}-\d{{4}}) (\S+) "
    r"(Regular|Visiting|Adhoc / Contractual|Other)", re.M)


def pdf_urls(inst: str, years=range(2019, 2027)) -> list[tuple[int, str, str]]:
    """[(ranking_year, category, url)] for the institute's DCS PDFs on nirfindia.org."""
    out = []
    for y in years:
        for page in RANK_PAGES:
            try:
                html = web().get(f"https://www.nirfindia.org/Rankings/{y}/{page}.html", ext="html")
            except PermanentHTTPError:
                continue
            except Exception as e:
                log.warning("NIRF page %s %s: %s", y, page, e)
                continue
            s = BeautifulSoup(html, "lxml")
            for tr in s.find_all("tr"):
                if NAME_PAT[inst].search(tr.get_text(" ")):
                    for a in tr.find_all("a", href=True):
                        if a["href"].lower().endswith(".pdf"):
                            out.append((y, page, a["href"] if a["href"].startswith("http") else f"https://www.nirfindia.org{a['href']}"))
                    break
    # one file per ranking year is enough (all categories share the faculty table)
    seen, uniq = set(), []
    for y, page, u in out:
        if y not in seen:
            seen.add(y)
            uniq.append((y, page, u))
    return uniq


def faculty_rows(pdf: bytes) -> list[dict]:
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
    i = text.find("Faculty Details")
    if i < 0:
        return []
    body = re.sub(r"\n(?!\d+ )", " ", text[i:])  # re-join wrapped table cells
    rows = []
    for m in ROW.finditer(body):
        sr, name, desig, gender, qual, exp, cur, join, leave, assoc = m.groups()
        rows.append({"name": re.sub(r"\s+\d+$", "", " ".join(name.split())), "designation": desig, "qualification": qual, "experience_months": int(exp),
                     "currently_working": cur == "Yes", "joining_date": join, "leaving_date": None if leave in ("--", "-") else leave,
                     "association": assoc})
    return rows


def summary_totals(inst: str) -> list[dict]:
    """'Number of faculty members entered' per ranking year from the public nirfindia.org files."""
    out = []
    for y, page, u in pdf_urls(inst):
        try:
            text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(web().get(u, ext="bin"))).pages)
        except Exception as e:
            log.warning("NIRF pdf %s: %s", u, e)
            continue
        m = re.search(r"Number of faculty members entered\s*(\d+)", text)
        out.append({"institution": inst, "ranking_year": y, "faculty_entered": int(m.group(1)) if m else None, "url": u})
    return out


def iiitd_own_files() -> list[tuple[int, str]]:
    """IIIT-D publishes its full DCS files (with per-faculty tables) on its own NIRF page."""
    from .web import fetch_html, links
    html = fetch_html("https://www.iiitd.ac.in/nirf", render_if_empty=False) or ""
    out = []
    for u, t in links(html, "https://www.iiitd.ac.in/nirf"):
        if "/docs/nirf/" in u and u.lower().endswith(".pdf"):
            m = re.search(r"/nirf/(20\d{2})/", u)
            out.append((int(m.group(1)) if m else 0, u))
    return sorted(set(out))


def iiitd_faculty() -> tuple[list[dict], list[dict]]:
    """Per-faculty rows from every IIIT-D DCS file that has a faculty table."""
    rows, files = [], []
    for y, u in iiitd_own_files():
        try:
            pdf = web().get(u, ext="bin")
        except Exception as e:
            log.warning("IIIT-D NIRF %s: %s", u, e)
            continue
        fr = faculty_rows(pdf)
        files.append({"ranking_year": y, "url": u, "rows": len(fr)})
        for r in fr:
            r.update({"ranking_year": y, "source_url": u})
        rows += fr
    return rows, files
