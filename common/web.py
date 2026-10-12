"""HTML helpers: cached page fetch with Playwright fallback, link/text extraction, and
identifier extraction (ORCID, DBLP, Scholar, CV) from faculty pages."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .config import CACHE, cfg
from .http import PermanentHTTPError
from .sources import web

log = logging.getLogger("web")

SKIP_HOMEPAGE_DOMAINS = (
    "linkedin.com", "scholar.google", "researchgate.net", "facebook.com", "twitter.com",
    "x.com", "instagram.com", "youtube.com", "orcid.org", "dblp.org", "dblp.uni-trier.de",
    "semanticscholar.org", "academia.edu", "mailto:",
)

ORCID_RE = re.compile(r"orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])")
DBLP_RE = re.compile(
    r"dblp(?:\.uni-trier\.de|\.org|\.dagstuhl\.de)/(?:pid/([\w/-]+?)(?:\.html|\.xml)?(?=[\"'\s<>?#]|$)"
    r"|pers/(?:hd|ht|hc)/[a-z0-9=]/([^\"'\s<>#?]+?)(?:\.html)?(?=[\"'\s<>?#]|$))"
)
SCHOLAR_RE = re.compile(r"scholar\.google\.[a-z.]+/citations\?[^\"'\s<>]*?user=([\w-]{12})")


def fetch_html(url: str, render_if_empty: bool = True) -> str | None:
    """Cached GET of an HTML page; falls back to Playwright rendering when the static HTML
    has almost no visible text (JS-rendered page). Returns None for 4xx / robots-disallowed."""
    try:
        html = web().get(url, ext="html")
    except PermanentHTTPError as e:
        if e.status == 403 and urlparse(url).netloc in cfg().get("browser_allowed_hosts", []):
            log.info("403 for %s; host is browser-allowed (user permission) -> rendering", url)
            return render(url)
        log.info("skip %s (%s)", url, e)
        return None
    except Exception as e:  # network failure after retries: logged, caller decides
        log.warning("fetch failed %s: %s", url, e)
        return None
    if render_if_empty and len(visible_text(html)) < 300:
        rendered = render(url)
        if rendered:
            return rendered
    return html


def render(url: str, wait_ms: int = 2500) -> str | None:
    """Render a JS page with headless Chromium. Cached under data/cache/web_rendered."""
    key = hashlib.sha1(url.encode()).hexdigest()
    p = CACHE / "web_rendered" / key[:2] / f"{key}.html"
    if p.exists():
        return p.read_text(errors="replace")
    if not web().allowed(url):
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("playwright not installed; cannot render %s", url)
        return None
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page(user_agent=cfg()["user_agent"], ignore_https_errors=False)
            page.goto(url, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(wait_ms)
            html = page.content()
            b.close()
    except Exception as e:
        log.warning("render failed %s: %s", url, e)
        return None
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html)
    (p.with_suffix(".meta.json")).write_text(json.dumps({"url": url, "rendered_at": time.strftime("%Y-%m-%dT%H:%M:%S")}))
    time.sleep(cfg()["rate_limits"]["web"])
    return html


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def visible_text(html: str) -> str:
    s = soup(html)
    for t in s(["script", "style", "noscript", "header", "footer", "nav"]):
        t.decompose()
    txt = s.get_text("\n")
    txt = re.sub(r"[ \t\xa0]+", " ", txt)
    return re.sub(r"\n\s*\n+", "\n", txt).strip()


def links(html: str, base: str) -> list[tuple[str, str]]:
    """[(absolute_url, anchor_text)]"""
    out = []
    for a in soup(html).find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("javascript:", "#")):
            continue
        out.append((urljoin(base, href), " ".join(a.get_text(" ").split())))
    return out


def same_site(url: str, home: str) -> bool:
    h1 = urlparse(url).netloc.removeprefix("www.")
    h2 = urlparse(home).netloc.removeprefix("www.")
    return h1 == h2


def extract_identifiers(html: str, base: str) -> dict:
    """ORCID, DBLP (pid or legacy pers path), Scholar user id, CV link from a page."""
    out: dict = {}
    raw = html
    if m := ORCID_RE.search(raw):
        out["orcid"] = m.group(1).upper()
    if m := DBLP_RE.search(raw):
        out["dblp_pid"] = m.group(1)
        out["dblp_legacy"] = None if m.group(1) else m.group(2)
    if m := SCHOLAR_RE.search(raw):
        out["scholar_url"] = f"https://scholar.google.com/citations?user={m.group(1)}"
    for url, text in links(html, base):
        t = text.lower()
        u = url.lower()
        if (re.search(r"\b(cv|curriculum vitae|resume|résumé|vita)\b", t) or re.search(r"(^|[/_-])(cv|vita|resume)[^/]*\.pdf$", u)) and "cvit" not in u:
            out.setdefault("cv_url", url)
    return out


def is_homepage_candidate(url: str) -> bool:
    u = url.lower()
    return u.startswith("http") and not any(d in u for d in SKIP_HOMEPAGE_DOMAINS)
