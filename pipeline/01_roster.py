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
from common.sources import dblp, wayback, web
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


def resolve_dblp(r: dict) -> None:
    """Fill dblp_pid: legacy URL -> pid via DBLP redirect; else DBLP author search with
    affiliation note. Non-unique matches go to review with candidates listed."""
    r["dblp_source"] = "homepage" if r.get("dblp_pid") else ""
    if not r.get("dblp_pid") and r.get("dblp_legacy"):
        try:
            xml = dblp().get(f"https://dblp.org/pers/xx/{r['dblp_legacy'][0].lower()}/{r['dblp_legacy']}.xml", ext="xml")
            if m := re.search(r'<dblpperson[^>]*pid="([^"]+)"', xml):
                r["dblp_pid"], r["dblp_source"] = m.group(1), "homepage_legacy"
        except Exception as e:
            log.info("legacy dblp resolve failed for %s: %s", r["name"], e)
    if r.get("dblp_pid"):
        r["dblp_confidence"] = 1.0
        return
    try:
        res = dblp().get("https://dblp.org/search/author/api", params={"q": r["name"], "format": "json", "h": 30})
    except Exception as e:
        log.warning("dblp search failed for %s: %s", r["name"], e)
        return
    hits = (res.get("result", {}).get("hits", {}) or {}).get("hit", []) or []
    cands = []
    for h in hits:
        info = h.get("info", {})
        notes = info.get("notes", {}).get("note", [])
        notes = notes if isinstance(notes, list) else [notes]
        affs = " | ".join(n.get("text", "") for n in notes if isinstance(n, dict) and n.get("@type") == "affiliation")
        sim = name_similarity(r["name"], info.get("author", ""))
        aliases = info.get("aliases", {}).get("alias", [])
        aliases = aliases if isinstance(aliases, list) else [aliases]
        sim = max([sim] + [name_similarity(r["name"], a) for a in aliases])
        pid = info.get("url", "").split("/pid/")[-1]
        cands.append({"pid": pid, "name": info.get("author"), "sim": round(sim, 2), "affil": affs,
                      "affil_match": bool(DBLP_AFFIL[r["institution"]].search(affs))})
    good = [c for c in cands if c["sim"] >= 0.85 and c["affil_match"]]
    if len(good) == 1:
        r["dblp_pid"], r["dblp_source"], r["dblp_confidence"] = good[0]["pid"], "dblp_search_affil", 0.9
    elif len(good) > 1:
        r["dblp_candidates"] = good
        r["dblp_confidence"] = 0.5
    else:
        named = [c for c in cands if c["sim"] >= 0.95]
        if named:
            r["dblp_candidates"] = named[:5]
            r["dblp_confidence"] = 0.3


# --------------------------------------------------------------------------------------
# Former faculty from Wayback snapshots
# --------------------------------------------------------------------------------------
NAME_LIKE = re.compile(r"^(?:(?:Dr|Prof)\.?\s+)?[A-Z][a-zA-Z.'\-]*(?:\s+[A-Z][a-zA-Z.'\-]*){1,4}$")
NOT_NAMES = {"home", "faculty", "research", "people", "about", "contact", "admissions", "news", "events",
             "academics", "centres", "centers", "students", "staff", "alumni", "publications", "visiting faculty",
             "adjunct faculty", "read more", "view profile", "know more", "computer science", "electronics"}
DESIG_NEAR = re.compile(r"(assistant|associate)?\s*professor|faculty|lecturer|scientist", re.I)


def wayback_list_urls(inst: str) -> list[str]:
    """Historical faculty-list URLs on the institute domain, via CDX (urlkey-collapsed)."""
    dom = urlparse(cfg()["institutes"][inst]["homepage"]).netloc.removeprefix("www.")
    try:
        rows = wayback().get(
            "https://web.archive.org/cdx/search/cdx",
            params={"url": dom, "matchType": "domain", "from": "2015", "to": "2026", "output": "json",
                    "fl": "original", "collapse": "urlkey", "filter": ["statuscode:200", "mimetype:text/html",
                    "original:.*[Ff]acult.*"], "limit": "20000"},
        )
    except Exception as e:
        log.warning("Wayback CDX unavailable for %s: %s", inst, e)
        return []
    urls = [r[0] for r in rows[1:]] if rows else []
    out = set()
    for u in urls:
        path = urlparse(u).path.lower().rstrip("/")
        q = urlparse(u).query
        if q and "page" not in q:
            continue
        last = path.rsplit("/", 1)[-1]
        if re.fullmatch(r"(people/)?faculty|faculty[-_]?(list|members|directory)?|(core|regular)[-_]faculty", last) or path.endswith("/people/faculty") or path in ("/faculty", "/people/faculty"):
            if "career" not in path and "recruit" not in path:
                out.add(u.split("#")[0])
    return sorted(out)


def wayback_names(inst: str, current_names: list[str]) -> list[dict]:
    yr0, yr1 = cfg()["years"]["start"], cfg()["years"]["end"] - 1
    found: dict[str, dict] = {}
    for lu in wayback_list_urls(inst):
        try:
            snaps = wayback().get(
                "https://web.archive.org/cdx/search/cdx",
                params={"url": lu, "from": str(yr0), "to": str(yr1), "output": "json",
                        "fl": "timestamp,original", "collapse": "timestamp:4", "filter": "statuscode:200"},
            )
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
                key = normalise(name)
                d = found.setdefault(key, {"name": name, "years": set(), "snapshots": set(), "context": ctx})
                d["years"].add(int(ts[:4]))
                d["snapshots"].add(f"https://web.archive.org/web/{ts}/{orig}")
    out = []
    for key, d in found.items():
        best = max((name_similarity(d["name"], c) for c in current_names), default=0)
        if best >= 0.85:
            continue  # still listed today (possibly under a variant)
        out.append({
            "name": d["name"], "first_seen": min(d["years"]), "last_seen": max(d["years"]),
            "n_snapshots": len(d["snapshots"]), "snapshot_example": sorted(d["snapshots"])[-1],
            "context": d["context"][:200], "closest_current_similarity": round(best, 2),
        })
    return out


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
        units = r.get("units") or []
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
            "centres_affiliated": r.get("centres_affiliated", ""),
            "admin_roles": r.get("admin_roles", ""),
            "joining_year": r.get("joining_year"),
            "joining_year_source": r.get("joining_year_source", ""),
            "joining_year_confidence": r.get("joining_year_confidence") or None,
            "joining_year_evidence": r.get("joining_year_evidence") or "",
            "phd": r.get("phd", ""),
            "status": r.get("status", "current"),
            "leaving_year": r.get("leaving_year"),
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
    for r in tqdm(rows, desc="DBLP"):
        resolve_dblp(r)

    review = []
    # Former faculty
    former_rows = []
    if not args.skip_wayback:
        for inst in ("IIIT-H", "IIIT-D"):
            if args.only and inst != args.only:
                continue
            cur = [r["name"] for r in rows if r["institution"] == inst]
            for f in wayback_names(inst, cur):
                former_rows.append({
                    "institution": inst, "name": f["name"], "designation_raw": "", "units": [],
                    "status": "former", "roster_source": "wayback", "leaving_year": f["last_seen"],
                    "notes": f"seen {f['first_seen']}-{f['last_seen']} in {f['n_snapshots']} snapshots; e.g. {f['snapshot_example']}",
                    "page_category": "",
                })
                review.append({"issue": "former_faculty_from_wayback", "institution": inst, "name": f["name"],
                               "detail": f"{f['first_seen']}-{f['last_seen']}; ctx: {f['context']}",
                               "evidence_url": f["snapshot_example"], "action": "confirm former core faculty (Y/N), add designation+unit"})
    for r in former_rows:
        resolve_dblp(r)
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
