"""Step 1 — Faculty roster for IIIT-H and IIIT-D  ->  data/faculty_roster.csv

Discovers faculty pages by crawling from the homepages (no hardcoded deep URLs), parses every
profile, visits personal homepages / CVs for ORCID, DBLP, Scholar and joining year, finds
former faculty via Wayback snapshots, resolves DBLP PIDs, and writes review files for
anything ambiguous.

Re-runnable: every request is cached under data/cache/.
"""
from __future__ import annotations

import argparse
import io
import re
from collections import defaultdict
from urllib.parse import urljoin, urlparse

import pandas as pd
from tqdm import tqdm

from common.config import DATA, PROCESSED, REVIEW, cfg, collection_date, setup_logging
from common.http import PermanentHTTPError
from common.joining import extract_joining_year
from common.names import name_similarity, normalise
from common.dblp_parse import persons_by_affiliation, persons_by_names
from common.sources import wayback, web
from common.web import (
    extract_identifiers,
    fetch_html,
    is_homepage_candidate,
    links,
    render,
    same_site,
    soup,
    visible_text,
)

log = setup_logging("01_roster")

CATEGORY_RULES = [  # (regex on URL path, designation_class)
    (r"adjunct", "adjunct"),
    (r"affiliate", "affiliate"),
    (r"distinguished", "distinguished"),
    (r"visiting", "visiting"),
    (r"emerit", "emeritus"),
    (r"pop-faculty|practice", "professor_of_practice"),
    (r"lecturer", "lecturer"),
    (r"guest", "guest"),
    (r"(^|/)(people/)?faculty/?$", "regular"),
]

IIITD_UNITS = {
    "CSE": "CSE", "ECE": "ECE", "CB": "CB", "COMPBIO": "CB", "HCD": "HCD", "DES": "HCD",
    "MATH": "MATH", "MATHS": "MATH", "AM": "MATH", "SSH": "SSH", "SS": "SSH",
}
IIITD_UNIT_NAMES = {
    "CSE": "Computer Science & Engineering", "ECE": "Electronics & Communications Engineering",
    "CB": "Computational Biology", "HCD": "Human-Centered Design", "MATH": "Mathematics",
    "SSH": "Social Sciences & Humanities",
}


UNIT_ALIASES = {"COGSCI": "CSL", "COGNITIVE SCIENCE": "CSL", "COMPBIO": "CB", "MATHS": "MATH", "DES": "HCD", "AM": "MATH", "SS": "SSH"}
_OFFICIAL: dict[str, dict[str, str]] = {}


def official_units(inst: str) -> dict[str, str]:
    """{acronym: full name} as published by the institute (IIIT-H research-centres page;
    IIIT-D department tabs on the faculty page)."""
    if inst in _OFFICIAL:
        return _OFFICIAL[inst]
    out: dict[str, str] = {}
    if inst == "IIIT-H":
        html = fetch_html("https://www.iiit.ac.in/research-centres/", render_if_empty=False) or ""
        txt = " ".join(visible_text(html).split())
        for name, acr in re.findall(r"([A-Z][A-Za-z,&'\- ]{3,90}?)\s*\(\s*([A-Z][A-Za-z]{1,8})\s*\)", txt):
            name = re.sub(r"^(?:Technology Research Cent(?:er|re)s|Domain Research Cent(?:er|re)s|Innovation Cent(?:er|re)s|The|the)\s+", "", name).strip()
            # keep research units only (drops 'Tata Consultancy Services (TCS)', '(IP)', '(AI)', ...)
            if acr not in out and len(name.split()) >= 2 and re.search(r"Cent(?:er|re)|\bLab\b|Group", name) and len(name.split()) <= 10:
                out[acr] = name
    else:
        out = dict(IIITD_UNIT_NAMES)
    _OFFICIAL[inst] = out
    return out


def normalise_unit(u: str, inst: str) -> str | None:
    """Map a profile's unit string to an official acronym; None if it cannot be mapped."""
    off = official_units(inst)
    if not u:
        return None
    key = u.strip().upper().replace(".", "")
    if u in off:
        return u
    if key in UNIT_ALIASES and UNIT_ALIASES[key] in off:
        return UNIT_ALIASES[key]
    if key in IIITD_UNITS and inst == "IIIT-D":
        return IIITD_UNITS[key]
    for acr in sorted(off, key=len, reverse=True):  # acronym mentioned inside a longer string
        if re.search(rf"\b{re.escape(acr)}\b", u):
            return acr
    from rapidfuzz import fuzz
    best = max(off.items(), key=lambda kv: fuzz.token_set_ratio(u.lower(), kv[1].lower()), default=None)
    if best and fuzz.token_set_ratio(u.lower(), best[1].lower()) >= 85:
        return best[0]
    return None


def designation_class(designation: str, page_category: str) -> str:
    d = (designation or "").lower()
    if page_category not in ("regular", ""):
        return page_category
    if "practice" in d:
        return "professor_of_practice"
    for k in ("adjunct", "visiting", "emerit", "distinguished", "affiliate", "guest"):
        if k in d:
            return {"emerit": "emeritus"}.get(k, k)
    if re.search(r"\b(assistant|associate)?\s*professor\b", d):
        return "core"
    if "lecturer" in d:
        return "lecturer"
    if "scientist" in d or "research" in d:
        return "research_staff"
    return "other"


def core_rank(designation: str) -> str:
    d = (designation or "").lower()
    if "assistant professor" in d:
        return "Assistant Professor"
    if "associate professor" in d:
        return "Associate Professor"
    if re.search(r"\bprofessor\b", d):
        return "Professor"
    return ""


def page_category(url: str) -> str | None:
    path = urlparse(url).path.lower().rstrip("/") + "/"
    for pat, cls in CATEGORY_RULES:
        if re.search(pat, path.rstrip("/")):
            return cls
    return None


# --------------------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------------------
def discover_category_pages(inst: str) -> dict[str, str]:
    """Crawl the homepage (and one level of 'people'/'faculty' hub pages) for faculty
    category list pages. Returns {url: category}."""
    home = cfg()["institutes"][inst]["homepage"]
    html = fetch_html(home, render_if_empty=True)
    if not html:
        raise SystemExit(f"Cannot fetch {inst} homepage {home}")
    found: dict[str, str] = {}
    frontier = [(home, html)]
    seen = {home}
    for depth in range(2):
        nxt = []
        for base, h in frontier:
            for url, text in links(h, base):
                url = url.split("#")[0]
                if not same_site(url, home) or url in seen:
                    continue
                path = urlparse(url).path.lower()
                if "career" in path or "recruit" in path or "position" in path:
                    continue
                if re.search(r"facult|people", path) and path.count("/") <= 3:
                    seen.add(url)
                    cat = page_category(url)
                    if cat and not re.search(r"/faculty/[a-z0-9-]+/?$", path):
                        found[url] = cat
                    elif depth == 0 and re.search(r"/people/?$", path):
                        hh = fetch_html(url)
                        if hh:
                            nxt.append((url, hh))
        frontier = nxt
    # canonicalise http/https + www duplicates
    canon: dict[str, str] = {}
    for u, c in found.items():
        key = urlparse(u).netloc.removeprefix("www.") + urlparse(u).path.rstrip("/")
        canon.setdefault(key, (u, c))
    out = {u: c for u, c in canon.values()}
    log.info("%s category pages: %s", inst, out)
    return out


def sitemap_urls(home: str, contains: str) -> list[str]:
    """Profile URLs from sitemaps declared in robots.txt (falls back to /sitemap.xml)."""
    base = f"{urlparse(home).scheme}://{urlparse(home).netloc}"
    maps = []
    try:
        robots = web().get(base + "/robots.txt", ext="txt")
        maps = re.findall(r"(?im)^sitemap:\s*(\S+)", robots)
    except PermanentHTTPError:
        pass
    maps = maps or [base + "/sitemap.xml"]
    out, queue, seen = [], list(maps), set()
    while queue:
        m = queue.pop()
        if m in seen or not m.endswith(".xml"):
            continue
        seen.add(m)
        try:
            xml = web().get(m, ext="xml")
        except PermanentHTTPError:
            continue
        locs = re.findall(r"<loc>(?:<!\[CDATA\[)?\s*(\S+?)\s*(?:\]\]>)?</loc>", xml)
        for loc in locs:
            if loc.endswith(".xml") and ("sitemap" in loc and (contains in loc or "index" in loc)):
                queue.append(loc)
            elif contains in loc:
                out.append(loc)
    return sorted(set(out))


# --------------------------------------------------------------------------------------
# IIIT-H
# --------------------------------------------------------------------------------------
def iiith_grid_profiles(list_url: str) -> list[str]:
    """Profile URLs from an Elementor 'Unlimited Elements' grid page, following ?ucpage=N."""
    html = fetch_html(list_url, render_if_empty=False) or ""
    urls = re.findall(r'data-link="(https?://[^"]+/faculty/[^"]+)"', html)
    m = re.search(r"num_pages&quot;:(\d+)", html)
    pages = int(m.group(1)) if m else 1
    for p in range(2, pages + 1):
        h = fetch_html(f"{list_url.rstrip('/')}/?ucpage={p}", render_if_empty=False) or ""
        urls += re.findall(r'data-link="(https?://[^"]+/faculty/[^"]+)"', h)
    if not urls:  # layout changed or JS-only: render
        h = render(list_url) or ""
        urls = [u for u, _ in links(h, list_url) if re.search(r"/faculty/[a-z0-9-]+/?$", u)]
    return list(dict.fromkeys(urls))


def _section(txt: str, start: str, stops: list[str]) -> str:
    i = txt.find(start)
    if i < 0:
        return ""
    j = len(txt)
    for s in stops:
        k = txt.find(s, i + len(start))
        if k > 0:
            j = min(j, k)
    return txt[i + len(start) : j].strip()


def parse_iiith_profile(url: str) -> dict | None:
    html = fetch_html(url, render_if_empty=True)
    if not html:
        return None
    s = soup(html)
    txt = visible_text(html)
    head = _section(txt, "CONTACT", ["Publications", "Research areas"])
    lines = [l.strip() for l in head.split("\n") if l.strip()]
    name = lines[0] if lines else (s.title.string.split(" - ")[0].strip() if s.title else "")
    desig_line = lines[1] if len(lines) > 1 else ""
    email = ""
    if m := re.search(r"([\w.+-]+)\s*\[\s*at\s*\]\s*([\w.-]+\.\w+)", head):
        email = f"{m.group(1)}@{m.group(2)}"
    centres_txt = _section(txt, "Research Centers/Labs", ["Awards & Achievements", "Research\nCentre/labs", "Explore"])
    # Unit acronyms in parentheses, in order of appearance; names without acronym kept whole.
    units = re.findall(r"\(([A-Z][A-Za-z0-9&\-]{1,12})\)", centres_txt)
    if not units and centres_txt:
        first = centres_txt.split("\n")[0]
        units = [first.split(" focuses")[0].split(" undertakes")[0].strip()[:80]]
    areas = _section(txt, "Research areas", ["Research Centers/Labs", "Awards"])
    anchors = {t.strip().lower(): u for u, t in links(html, url)}
    return {
        "name": name,
        "designation_raw": desig_line,
        "email": email,
        "units": list(dict.fromkeys(units)),
        "unit_text": centres_txt[:300],
        "research_areas": " ".join(areas.split())[:300],
        "institute_profile": url,
        "institute_webpage": anchors.get("institute webpage", ""),
        "publications_portal": anchors.get("publications", ""),
        "homepage": anchors.get("personal homepage", ""),
        "page_ids": extract_identifiers(html, url),
    }


def build_iiith() -> list[dict]:
    inst = "IIIT-H"
    home = cfg()["institutes"][inst]["homepage"]
    cats = discover_category_pages(inst)
    url_cat: dict[str, str] = {}
    for list_url, cat in cats.items():
        for u in iiith_grid_profiles(list_url):
            # an explicit non-regular category page wins over the main grid
            if u not in url_cat or url_cat[u] == "regular":
                url_cat[u] = cat
    sm = sitemap_urls(home, "/faculty/")
    sm = [u for u in sm if re.search(r"/faculty/[a-z0-9-]+/?$", u)]
    for u in sm:
        url_cat.setdefault(u, "sitemap_only")
    log.info("IIIT-H: %d profile URLs (%d from category pages, %d sitemap-only)",
             len(url_cat), sum(c != "sitemap_only" for c in url_cat.values()),
             sum(c == "sitemap_only" for c in url_cat.values()))
    rows = []
    for u, cat in tqdm(sorted(url_cat.items()), desc="IIIT-H profiles"):
        p = parse_iiith_profile(u)
        if not p or not p["name"]:
            log.warning("could not parse %s", u)
            continue
        p["page_category"] = "regular" if cat == "sitemap_only" else cat
        p["in_listing"] = cat != "sitemap_only"
        p["institution"] = inst
        rows.append(p)
    return rows


# --------------------------------------------------------------------------------------
# IIIT-D
# --------------------------------------------------------------------------------------
def parse_iiitd_cards(list_url: str) -> list[dict]:
    html = fetch_html(list_url, render_if_empty=True) or ""
    s = soup(html)
    out = []
    cards = s.select(".facultycard") or s.select(".post-card")
    for c in cards:
        a = c.select_one(".team-title a") or c.find("a", href=True)
        if not a:
            continue
        name = " ".join(a.get_text(" ").split())
        # adjunct/visiting cards: "Abhinav Dhall (HCD)" — unit in the name, no profile page
        name_units = []
        if m := re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", name):
            name = m.group(1).strip()
            name_units = [IIITD_UNITS.get(u.strip().upper().replace(".", ""), u.strip()) for u in m.group(2).split(",") if u.strip()]
        sub = c.select_one(".team-subtitle")
        desig = " ".join(sub.get_text(" ").split()) if sub else ""
        email = ""
        if m := c.find("a", href=re.compile(r"^mailto:")):
            email = m["href"].removeprefix("mailto:").strip()
        phd = ""
        for p in c.select(".team-description p"):
            t = p.get_text(" ").strip()
            if t.lower().startswith("ph"):
                phd = t
        out.append({
            "name": name,
            "designation_raw": desig,
            "email": email,
            "phd": phd,
            "institute_profile": "" if urljoin(list_url, a["href"]).rstrip("/") == list_url.rstrip("/") else urljoin(list_url, a["href"]),
            "card_type": c.get("type", ""),
            "name_units": name_units,
        })
    if not out:
        log.warning("no cards parsed on %s", list_url)
    return out


def split_iiitd_designation(raw: str) -> tuple[str, list[str], list[str]]:
    """'Head (ECE), Professor (ECE, CSE)' -> ('Professor', ['ECE','CSE'], ['Head (ECE)'])"""
    parts = [p.strip() for p in re.split(r",\s*(?![^()]*\))", raw) if p.strip()]
    desig, units, roles = "", [], []
    for p in parts:
        m = re.match(r"(.+?)\s*\(([^)]*)\)", p)
        title = (m.group(1) if m else p).strip()
        if re.search(r"professor|lecturer|scientist|faculty|fellow", title, re.I) and not desig:
            desig = title
            if m:
                units = [IIITD_UNITS.get(u.strip().upper().replace(".", ""), u.strip()) for u in m.group(2).split(",")]
        else:
            roles.append(p)
    return desig or raw, units, roles


def parse_iiitd_profile(url: str) -> dict:
    html = fetch_html(url, render_if_empty=True)
    if not html:
        return {}
    txt = visible_text(html)
    homepage = ""
    for u, t in links(html, url):
        if t.strip().lower() in ("web profile", "homepage", "home page", "personal homepage", "website") and is_homepage_candidate(u):
            homepage = u
            break
    centres = _section(txt, "Affiliated Centres & Labs", ["Copyright"])
    interests = _section(txt, "Research Interests", ["Teaching Interests", "Affiliated Centres"])
    bio = _section(txt, "Profile", ["Research Interests"])
    return {
        "homepage": homepage,
        "centres_affiliated": "; ".join(l.strip() for l in centres.split("\n") if l.strip())[:300],
        "research_areas": "; ".join(l.strip() for l in interests.split("\n") if l.strip())[:300],
        "bio": bio[:3000],
        "page_ids": extract_identifiers(html, url),
    }


def build_iiitd() -> list[dict]:
    inst = "IIIT-D"
    cats = discover_category_pages(inst)
    rows, seen = [], {}
    for list_url, cat in cats.items():
        for card in parse_iiitd_cards(list_url):
            key = card["institute_profile"].rstrip("/") or f"name:{normalise(card['name'])}"
            if key in seen and seen[key]["page_category"] == "regular":
                continue
            card["page_category"] = cat
            seen[key] = card
    log.info("IIIT-D: %d people across %d category pages", len(seen), len(cats))
    for card in tqdm(list(seen.values()), desc="IIIT-D profiles"):
        desig, units, roles = split_iiitd_designation(card["designation_raw"])
        units = units or card.get("name_units", [])
        if not card["designation_raw"]:
            desig = {"adjunct": "Adjunct Faculty", "visiting": "Visiting Faculty", "emeritus": "Professor Emeritus",
                     "professor_of_practice": "Professor of Practice"}.get(card["page_category"], "")
        if card["institute_profile"]:
            card.update(parse_iiitd_profile(card["institute_profile"]))
        card.update({
            "institution": inst,
            "designation_main": desig,
            "units": units,
            "admin_roles": "; ".join(roles),
            "in_listing": True,
        })
        rows.append(card)
    return rows


# --------------------------------------------------------------------------------------
# Homepages, CVs, joining year
# --------------------------------------------------------------------------------------
def pdf_text(url: str) -> str:
    try:
        data = web().get(url, ext="bin")
    except Exception as e:
        log.info("CV fetch failed %s: %s", url, e)
        return ""
    try:
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in r.pages[:8])
    except Exception as e:
        log.info("CV parse failed %s: %s", url, e)
        return ""


def enrich_from_pages(r: dict) -> None:
    """Visit homepage, institute webpage and CV; merge identifiers; extract joining year."""
    inst = r["institution"]
    ids = dict(r.get("page_ids") or {})
    texts: list[tuple[str, str]] = []  # (source_label, text)
    if r.get("bio"):
        texts.append(("institute_profile", r["bio"]))
    pages = [("institute_webpage", r.get("institute_webpage")), ("homepage", r.get("homepage"))]
    for label, u in pages:
        if not u or not is_homepage_candidate(u):
            continue
        h = fetch_html(u, render_if_empty=True)
        if not h:
            continue
        for k, v in extract_identifiers(h, u).items():
            if v and not ids.get(k):
                ids[k] = v
        texts.append((label, visible_text(h)))
        # one level down: an "About"/"Bio"/"CV" page on the same personal site
        for lu, lt in links(h, u):
            if same_site(lu, u) and re.search(r"\b(about|bio|cv|vita|resume|people/)", (lt + " " + lu).lower()) and not lu.lower().endswith(".pdf"):
                hh = fetch_html(lu, render_if_empty=False)
                if hh:
                    texts.append((label + "_subpage", visible_text(hh)))
                    for k, v in extract_identifiers(hh, lu).items():
                        if v and not ids.get(k):
                            ids[k] = v
                break
    if ids.get("cv_url"):
        t = pdf_text(ids["cv_url"]) if ids["cv_url"].lower().endswith(".pdf") else ""
        if t:
            texts.append(("cv", t))
    best = (None, 0.0, None, None)
    for label, t in texts:
        y, c, ev = extract_joining_year(t, inst)
        if y and c > best[1]:
            best = (y, c, ev, label)
    r.update({k: ids.get(k, "") for k in ("orcid", "dblp_pid", "dblp_legacy", "scholar_url", "cv_url")})
    r["joining_year"], r["joining_year_confidence"], r["joining_year_evidence"], src = best
    r["joining_year_source"] = f"stated_{src}" if src else ""


# --------------------------------------------------------------------------------------
# DBLP
# --------------------------------------------------------------------------------------
DBLP_AFFIL = {
    "IIIT-H": re.compile(r"IIIT Hyderabad|International Institute of Information Technology,? Hyderabad|IIIT-H\b", re.I),
    "IIIT-D": re.compile(r"IIIT[- ]?Delhi|Indraprastha Institute of Information Technology|IIIT-D\b", re.I),
}


_AFFIL_PERSONS: list[dict] | None = None
_NAME_HITS: list[dict] | None = None


def prefetch_dblp_names(rows: list[dict]) -> None:
    """One batched SPARQL pass over every name variant of every roster person."""
    global _NAME_HITS
    variants = sorted({v for r in rows for v in name_variants_for_dblp(r["name"])})
    try:
        _NAME_HITS = persons_by_names(variants)
    except Exception as e:
        log.warning("dblp batched name lookup failed: %s", e)
        _NAME_HITS = []


def affiliated_dblp_persons() -> list[dict]:
    global _AFFIL_PERSONS
    if _AFFIL_PERSONS is None:
        _AFFIL_PERSONS = persons_by_affiliation(["iiit hyderabad", "iiit-hyderabad", "international institute of information technology, hyderabad",
                                                 "international institute of information technology hyderabad", "iiit-h,",
                                                 "indraprastha institute", "iiit delhi", "iiit-delhi", "iiitd"])
    return _AFFIL_PERSONS


def name_variants_for_dblp(name: str) -> list[str]:
    """DBLP writes names like 'C. V. Jawahar' or 'Anoop M. Namboodiri'."""
    toks = name.replace(".", " ").split()
    out = {name, " ".join(toks)}
    dotted = " ".join(t + "." if len(t) == 1 else t for t in toks)
    out.add(dotted)
    if len(toks) >= 3:  # middle names as initials
        out.add(" ".join([toks[0]] + [t[0] + "." for t in toks[1:-1]] + [toks[-1]]))
    return sorted(out)


def resolve_dblp(r: dict) -> None:
    """Fill dblp_pid via DBLP SPARQL: homepage link > institute-affiliated DBLP person with a
    matching name > unique exact-name match with matching affiliation. Ambiguous -> review."""
    r["dblp_source"] = "homepage" if r.get("dblp_pid") else ""
    if r.get("dblp_pid"):
        r["dblp_confidence"] = 1.0
        return
    names = [r["name"]] + ([r["dblp_legacy"].split(":")[-1]] if r.get("dblp_legacy") else [])
    aff = [p for p in affiliated_dblp_persons() if DBLP_AFFIL[r["institution"]].search(" | ".join(p["affiliations"]))
           and max(name_similarity(n, p["name"]) for n in names) >= 0.85]
    if len(aff) == 1:
        r["dblp_pid"], r["dblp_source"], r["dblp_confidence"] = aff[0]["pid"], "dblp_affiliation+name", 0.92
        return
    wanted = set(name_variants_for_dblp(r["name"]))
    if _NAME_HITS is None:
        prefetch_dblp_names([r])
    cands = [c for c in _NAME_HITS if c["query_name"] in wanted]
    by_pid = {}
    for c in cands:
        by_pid.setdefault(c["pid"], c)
    good = [c for c in by_pid.values() if DBLP_AFFIL[r["institution"]].search(c["affiliation"] or "")]
    if len(good) == 1:
        r["dblp_pid"], r["dblp_source"], r["dblp_confidence"] = good[0]["pid"], "dblp_name+affiliation", 0.9
    elif len(by_pid) == 1 and not aff:
        c = next(iter(by_pid.values()))
        # unique exact name in all of DBLP but no affiliation recorded: plausible, needs confirming in step 2
        r["dblp_pid"], r["dblp_source"], r["dblp_confidence"] = c["pid"], "dblp_unique_exact_name", 0.7
    elif by_pid or aff:
        r["dblp_candidates"] = [{"pid": c["pid"], "name": c["name"], "sim": round(name_similarity(r["name"], c["name"]), 2), "affil": c.get("affiliation", "")}
                                for c in list(by_pid.values())[:6]] + [{"pid": a["pid"], "name": a["name"], "sim": 1.0, "affil": "; ".join(a["affiliations"])} for a in aff]
        r["dblp_confidence"] = 0.5


# --------------------------------------------------------------------------------------
# Former faculty from Wayback snapshots
# --------------------------------------------------------------------------------------
NAME_LIKE = re.compile(r"^(?:(?:Dr|Prof)\.?\s+)?[A-Z][a-zA-Z.'\-]*(?:\s+[A-Z][a-zA-Z.'\-]*){1,4}$")
NON_PERSON_TOKENS = {
    "about", "links", "link", "internal", "admission", "admissions", "body", "governing", "group", "science", "sciences", "sci",
    "maths", "math", "mathematics", "equations", "differential", "partial", "students", "student", "facts", "quick", "coverage",
    "media", "information", "right", "identity", "graphic", "directory", "contact", "twitter", "facebook", "youtube", "linkedin",
    "instagram", "tenders", "webmail", "outreach", "advisor", "research", "scientists", "ugc", "post", "phd", "bsc", "sponsored",
    "rolling", "computational", "biology", "social", "cog", "centre", "center", "lab", "department", "programme", "program",
    "faculty", "staff", "project", "coordinator", "engineering", "electronics", "communication", "design", "humanities",
    "sahaai", "office", "dean", "registrar", "library", "campus", "news", "events", "alumni", "placement", "careers", "login",
}
NOT_NAMES = {"home", "faculty", "research", "people", "about", "contact", "admissions", "news", "events",
             "academics", "centres", "centers", "students", "staff", "alumni", "publications", "visiting faculty",
             "adjunct faculty", "read more", "view profile", "know more", "computer science", "electronics"}
DESIG_NEAR = re.compile(r"(assistant|associate)?\s*professor|faculty|lecturer|scientist", re.I)


def wayback_list_urls(inst: str) -> list[str]:
    """Historical faculty-list URLs, via path-prefix CDX queries (a domain-wide query is too
    large for the CDX server)."""
    dom = urlparse(cfg()["institutes"][inst]["homepage"]).netloc.removeprefix("www.")
    out = set()
    for prefix in (f"{dom}/people/", f"{dom}/faculty", f"www.{dom}/people/", f"www.{dom}/faculty"):
        try:
            rows = wayback().get("https://web.archive.org/cdx/search/cdx",
                                 params={"url": prefix, "matchType": "prefix", "from": "2015", "to": "2026", "output": "json",
                                         "fl": "original", "collapse": "urlkey", "filter": ["statuscode:200", "mimetype:text/html"], "limit": "5000"})
        except Exception as e:
            log.warning("Wayback CDX %s: %s", prefix, e)
            continue
        for (u,) in (rows[1:] if rows else []):
            path = urlparse(u).path.lower().rstrip("/")
            if urlparse(u).query:
                continue
            if path in ("/faculty", "/people/faculty") and "career" not in path:
                out.add(u.split("#")[0].replace(":80/", "/"))
    # one canonical URL per path (http/https/www variants are the same page)
    canon = {}
    for u in sorted(out):
        canon.setdefault(urlparse(u).path.rstrip("/"), u)
    log.info("%s Wayback list URLs: %s", inst, list(canon.values()))
    return list(canon.values())


DESIG_RE = re.compile(r"(Distinguished Professor|Professor Emeritus|Emeritus Professor|Adjunct (?:Assistant |Associate )?Professor|Visiting (?:Assistant |Associate )?Professor|"
                      r"Assistant Professor|Associate Professor|Professor of Practice|Professor|Lecturer|Research Scientist|Scientist)", re.I)


def wayback_presence(inst: str) -> pd.DataFrame:
    """One row per (snapshot year, name) seen on the institute's archived faculty-list pages,
    with the designation shown next to the name."""
    yr0, yr1 = cfg()["years"]["start"] - 1, cfg()["years"]["end"] - 1
    rows = []
    for lu in wayback_list_urls(inst):
        try:
            snaps = wayback().get("https://web.archive.org/cdx/search/cdx",
                                  params={"url": lu, "from": str(yr0), "to": str(yr1), "output": "json",
                                          "fl": "timestamp,original", "collapse": "timestamp:4", "filter": "statuscode:200"})
        except Exception as e:
            log.warning("CDX snapshots failed %s: %s", lu, e)
            continue
        for ts, orig in (snaps[1:] if snaps else []):
            try:
                html = wayback().get(f"https://web.archive.org/web/{ts}id_/{orig}", ext="html")
            except Exception as e:
                log.info("snapshot fetch failed %s %s: %s", ts, orig, e)
                continue
            for name, ctx in candidate_names(html):
                m = DESIG_RE.search(ctx[len(name):len(name) + 120])
                rows.append({"institution": inst, "snapshot": ts, "year": int(ts[:4]), "name": name,
                             "designation_seen": m.group(1).title() if m else "", "snapshot_url": f"https://web.archive.org/web/{ts}/{orig}"})
    return pd.DataFrame(rows)


def wayback_names(inst: str, current_names: list[str], presence: pd.DataFrame) -> list[dict]:
    """Names on archived lists that are not on today's site (fuzzy), with years seen and the
    designation they were listed under."""
    if presence.empty:
        return []
    out = []
    # order-insensitive key so 'B. S. Lakshmi' and 'Lakshmi B.S' are one person
    for key, g in presence.assign(key=presence.name.map(lambda n: " ".join(sorted(normalise(n).split())))).groupby("key"):
        name = g.name.iloc[-1]
        best = max((name_similarity(name, c) for c in current_names), default=0)
        if best >= 0.85:
            continue
        desig = g.designation_seen.replace("", pd.NA).dropna()
        if desig.empty:
            continue  # never shown with a designation: menu text, headings, or non-faculty
        out.append({"name": name, "first_seen": int(g.year.min()), "last_seen": int(g.year.max()), "n_snapshots": g.snapshot.nunique(),
                    "snapshot_example": g.snapshot_url.iloc[-1], "designation_seen": desig.iloc[-1] if len(desig) else "",
                    "context": "", "closest_current_similarity": round(best, 2)})
    return out


def first_listed(presence: pd.DataFrame, name: str) -> tuple[int | None, int | None, str]:
    """(first year listed, earliest snapshot year, evidence) for a current faculty member."""
    if presence.empty:
        return None, None, ""
    hit = presence[presence.name.map(lambda n: name_similarity(n, name) >= 0.85)]
    first_snap = int(presence.year.min())
    if hit.empty:
        return None, first_snap, ""
    y = int(hit.year.min())
    prev = presence[presence.year < y].snapshot.max()
    first = hit.sort_values("snapshot").snapshot.iloc[0]
    return y, first_snap, f"first listed in Wayback snapshot {first[:8]}" + (f"; absent from {str(prev)[:8]}" if isinstance(prev, str) else "")


def candidate_names(html: str) -> list[tuple[str, str]]:
    """Person names on an archived faculty list page: short capitalised strings in
    headings/links/strong tags that have a designation word within the next ~200 chars."""
    s = soup(html)
    for t in s(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    full = " ".join(s.get_text(" ").split())
    out = []
    for tag in s.find_all(["h2", "h3", "h4", "h5", "a", "strong", "b", "td", "span", "div", "p"]):
        if tag.find(["h2", "h3", "h4", "div", "p", "table"]):
            continue
        t = " ".join(tag.get_text(" ").split())
        if not (5 <= len(t) <= 45) or not NAME_LIKE.match(t) or t.lower() in NOT_NAMES:
            continue
        if any(w in t.lower() for w in ("professor", "faculty", "department", "centre", "center", "institute", "lab")):
            continue
        if {re.sub(r"[^a-z]", "", w) for w in t.lower().split()} & NON_PERSON_TOKENS:
            continue
        i = full.find(t)
        ctx = full[i : i + 220] if i >= 0 else ""
        if DESIG_NEAR.search(ctx[len(t):]):
            out.append((re.sub(r"^(Dr|Prof)\.?\s+", "", t), ctx))
    return list({n: (n, c) for n, c in out}.values())


# --------------------------------------------------------------------------------------
# IRINS cross-check (best effort; portals may block automated clients)
# --------------------------------------------------------------------------------------
IRINS_HOSTS = {"IIIT-H": "https://iiit.irins.org/", "IIIT-D": "https://iiitd.irins.org/"}


def irins_names(inst: str) -> list[str] | None:
    base = IRINS_HOSTS[inst]
    # IRINS answers 403 to plain scripts; fetch_html renders it in a browser because the host is
    # in config browser_allowed_hosts (robots.txt allows us; user has institutional permission).
    html = fetch_html(base + "faculty/index/", render_if_empty=True)
    if not html:
        return None
    names = [" ".join(a.get_text(" ").split()) for a in soup(html).select("a[href*='profile/']")]
    names = [n for n in names if 4 <= len(n) <= 60]
    return sorted(set(names)) or None


# --------------------------------------------------------------------------------------
# Assemble
# --------------------------------------------------------------------------------------
def finalise(rows: list[dict]) -> pd.DataFrame:
    cdate = collection_date()
    out = []
    for r in rows:
        inst = r["institution"]
        desig_raw = r.get("designation_main") or r.get("designation_raw", "")
        cls = designation_class(desig_raw, r.get("page_category", ""))
        rank = core_rank(desig_raw) if cls == "core" else ""
        raw_units = r.get("units") or []
        units = list(dict.fromkeys(x for x in (normalise_unit(u, inst) for u in raw_units) if x))
        unmapped = [u for u in raw_units if not normalise_unit(u, inst)]
        variants = {r["name"], normalise(r["name"]).title()}
        if r.get("email"):
            variants.add(r["email"].split("@")[0])
        email_dom = r["email"].split("@")[-1].lower() if r.get("email") else ""
        out.append({
            "faculty_id": f"{inst}:{normalise(r['name']).replace(' ', '_')}",
            "institution": inst,
            "name": r["name"],
            "name_variants": "; ".join(sorted(v for v in variants if v)),
            "designation": rank or desig_raw,
            "designation_raw": r.get("designation_raw", ""),
            "designation_class": cls,
            "is_core": cls == "core",
            "unit": units[0] if units else "",
            "units_secondary": "; ".join(units[1:]),
            "unit_type": cfg()["institutes"][inst]["unit_type"],
            "unit_text": r.get("unit_text", ""),
            "units_unmapped": "; ".join(unmapped),
            "centres_affiliated": r.get("centres_affiliated", ""),
            "admin_roles": r.get("admin_roles", ""),
            "joining_year": r.get("joining_year"),
            "joining_year_source": r.get("joining_year_source", ""),
            "joining_year_confidence": r.get("joining_year_confidence") or None,
            "joining_year_evidence": r.get("joining_year_evidence") or "",
            "phd": r.get("phd", ""),
            "status": r.get("status", "current"),
            "leaving_year": r.get("leaving_year"),
            "joined_by_year": r.get("joined_by_year"),
            "joined_after_year": r.get("joined_after_year"),
            "homepage": r.get("homepage", ""),
            "institute_profile": r.get("institute_profile", ""),
            "publications_portal": r.get("publications_portal", ""),
            "email_domain": email_dom,
            "orcid": r.get("orcid", ""),
            "dblp_pid": r.get("dblp_pid", ""),
            "dblp_source": r.get("dblp_source", ""),
            "dblp_confidence": r.get("dblp_confidence"),
            "scholar_url": r.get("scholar_url", ""),
            "cv_url": r.get("cv_url", ""),
            "openalex_ids": "",
            "research_areas": r.get("research_areas", ""),
            "roster_source": r.get("roster_source", "official_site"),
            "notes": r.get("notes", ""),
            "collected_at": cdate,
        })
    df = pd.DataFrame(out)
    # same person listed twice (e.g. both grid and adjunct page) -> keep the most specific
    df = df.sort_values(["faculty_id", "is_core"], ascending=[True, False]).drop_duplicates("faculty_id")
    return df.reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-wayback", action="store_true")
    ap.add_argument("--only", choices=["IIIT-H", "IIIT-D"])
    args = ap.parse_args()

    rows: list[dict] = []
    if args.only in (None, "IIIT-H"):
        rows += build_iiith()
    if args.only in (None, "IIIT-D"):
        rows += build_iiitd()

    for r in tqdm(rows, desc="homepages/CVs"):
        enrich_from_pages(r)
    prefetch_dblp_names(rows)
    for r in tqdm(rows, desc="DBLP"):
        resolve_dblp(r)

    review = []
    # Former faculty + joining-year proxy from yearly Wayback snapshots
    former_rows = []
    presence_all: list[pd.DataFrame] = []
    if not args.skip_wayback:
        for inst in ("IIIT-H", "IIIT-D"):
            if args.only and inst != args.only:
                continue
            cur = [r["name"] for r in rows if r["institution"] == inst]
            pres = wayback_presence(inst)
            presence_all.append(pres)
            # joining-year proxy for current faculty: first year on the archived list
            for r in rows:
                if r["institution"] != inst or r.get("joining_year"):
                    continue
                y, first_snap, ev = first_listed(pres, r["name"])
                if y and first_snap and y > first_snap:
                    r["joining_year"], r["joining_year_confidence"], r["joining_year_evidence"] = y, 0.6, ev
                    r["joining_year_source"] = "wayback_first_listed"
                elif y and first_snap and y == first_snap:
                    r["joined_by_year"] = first_snap  # listed in the earliest snapshot: joined on/before it
                elif y is None and not pres.empty:
                    r["joined_after_year"] = int(pres[pres.snapshot_url.str.contains("/people/faculty")].year.max()
                                                 if pres.snapshot_url.str.contains("/people/faculty").any() else pres.year.max())
            for f in wayback_names(inst, cur, pres):
                d = f["designation_seen"]
                former_rows.append({
                    "institution": inst, "name": f["name"], "designation_raw": d, "units": [],
                    "status": "former", "roster_source": "wayback", "leaving_year": f["last_seen"],
                    "notes": f"listed {f['first_seen']}-{f['last_seen']} in {f['n_snapshots']} yearly snapshots as '{d}'; e.g. {f['snapshot_example']}",
                    "page_category": "",
                })
                review.append({"issue": "former_faculty_from_wayback", "institution": inst, "name": f["name"],
                               "detail": f"{f['first_seen']}-{f['last_seen']} as '{d}'",
                               "evidence_url": f["snapshot_example"], "action": "confirm departure; set unit"})
    if former_rows:
        prefetch_dblp_names(rows + former_rows)
    for r in former_rows:
        resolve_dblp(r)
    if presence_all:
        pd.concat(presence_all).to_csv(PROCESSED / "wayback_presence.csv", index=False)
    df = finalise(rows + former_rows)
    # former: designation unknown from generic snapshot parsing -> provisional class
    df.loc[df.status.eq("former") & df.designation_class.eq("other"), "designation_class"] = "former_unverified"

    # IRINS cross-check
    irins_report = {}
    for inst in ("IIIT-H", "IIIT-D"):
        names = irins_names(inst)
        if names is None:
            irins_report[inst] = "unavailable (portal blocks automated access)"
            continue
        ours = df[df.institution.eq(inst)].name.tolist()
        missing = [n for n in names if max((name_similarity(n, o) for o in ours), default=0) < 0.85]
        irins_report[inst] = f"{len(names)} IRINS profiles, {len(missing)} not in roster"
        for n in missing:
            review.append({"issue": "in_irins_not_roster", "institution": inst, "name": n, "detail": "",
                           "evidence_url": IRINS_HOSTS[inst], "action": "add to roster? (Y/N + status)"})

    # Review items
    for _, r in df.iterrows():
        if r.status == "current" and r.is_core and not r.unit:
            review.append({"issue": "missing_unit", "institution": r.institution, "name": r["name"],
                           "detail": r.unit_text, "evidence_url": r.institute_profile, "action": "set unit"})
        if r.joining_year_confidence is not None and pd.notna(r.joining_year_confidence) and r.joining_year_confidence < 0.8:
            review.append({"issue": "joining_year_low_confidence", "institution": r.institution, "name": r["name"],
                           "detail": f"{r.joining_year}: {r.joining_year_evidence}", "evidence_url": r.homepage or r.institute_profile,
                           "action": "confirm joining year"})
        if r.designation_class in ("other", "professor_of_practice", "research_staff", "former_unverified"):
            review.append({"issue": f"designation_{r.designation_class}", "institution": r.institution, "name": r["name"],
                           "detail": r.designation_raw, "evidence_url": r.institute_profile, "action": "include in core analysis? (Y/N)"})
    for r in rows + former_rows:
        if r.get("dblp_candidates"):
            review.append({"issue": "dblp_ambiguous", "institution": r["institution"], "name": r["name"],
                           "detail": "; ".join(f"{c['pid']} ({c['name']}, sim {c['sim']}, {c['affil'][:60]})" for c in r["dblp_candidates"]),
                           "evidence_url": "", "action": "pick the right DBLP pid or 'none'"})

    # name collisions across institutes
    names = df[["institution", "name"]].values.tolist()
    for i, (ia, na) in enumerate(names):
        for ib, nb in names[i + 1 :]:
            if ia != ib and name_similarity(na, nb) >= 0.9:
                review.append({"issue": "name_collision_across_institutes", "institution": f"{ia}/{ib}", "name": f"{na} / {nb}",
                               "detail": "", "evidence_url": "", "action": "same person (moved)? different?"})

    for _, r in df[df.units_unmapped.ne("")].iterrows():
        review.append({"issue": "unit_not_in_official_list", "institution": r.institution, "name": r["name"],
                       "detail": r.units_unmapped, "evidence_url": r.institute_profile, "action": "map to an official unit"})
    import json as _json
    (PROCESSED / "units_official.json").write_text(_json.dumps({i: official_units(i) for i in ("IIIT-H", "IIIT-D")}, indent=1))
    DATA.mkdir(exist_ok=True)
    df.to_csv(DATA / "faculty_roster.csv", index=False)
    pd.DataFrame(review).to_csv(REVIEW / "roster_to_review.csv", index=False)
    (PROCESSED / "irins_check.txt").write_text("\n".join(f"{k}: {v}" for k, v in irins_report.items()))
    summary(df, irins_report, len(review))


def summary(df: pd.DataFrame, irins: dict, n_review: int) -> None:
    print("\n=== ROSTER SUMMARY ===")
    for inst, g in df.groupby("institution"):
        cur = g[g.status.eq("current")]
        print(f"\n{inst}: {len(cur)} current listed ({cur.is_core.sum()} core), {g.status.eq('former').sum()} former candidates")
        print("  by class:", cur.designation_class.value_counts().to_dict())
        core = cur[cur.is_core]
        print("  core by unit:", core.unit.replace("", "(none)").value_counts().to_dict())
        print("  core by rank:", core.designation.value_counts().to_dict())
        print(f"  ids (core): orcid {core.orcid.ne('').mean():.0%}, dblp {core.dblp_pid.ne('').mean():.0%}, "
              f"scholar {core.scholar_url.ne('').mean():.0%}, homepage {core.homepage.ne('').mean():.0%}, "
              f"joining year {core.joining_year.notna().mean():.0%}")
    print("\nIRINS:", irins)
    print(f"Review items: {n_review} -> review/roster_to_review.csv")


if __name__ == "__main__":
    main()
