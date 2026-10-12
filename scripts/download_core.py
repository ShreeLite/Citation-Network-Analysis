"""Download CORE conference-ranking exports into data/external/core/.

Run this yourself:   make core      (or: .venv/bin/python scripts/download_core.py)

The CORE portal's robots.txt disallows AI agents (Claude-User, anthropic-ai, GPTBot, ...)
but allows ordinary clients on the export path, so this is a user-run script and is not
called by the automated pipeline. It checks robots.txt for its own User-Agent and fetches
one export per edition with a polite delay.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from common.robots import Robots  # noqa: E402  (RFC 9309 longest-match semantics)
OUT = ROOT / "data" / "external" / "core"
UA = "DPCN-Group9-IIIT research mapping (mailto:krisjainhzb@gmail.com)"
BASE = "https://portal.core.edu.au/conf-ranks/"
EDITIONS = ["CORE2023", "CORE2021", "CORE2020", "CORE2018", "CORE2017", "CORE2014", "ICORE2026"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rp = Robots(requests.get("https://portal.core.edu.au/robots.txt", headers={"User-Agent": UA}, timeout=60).text)
    url0 = f"{BASE}?search=&by=all&source=CORE2023&sort=arank&page=1&do=Export"
    if not rp.can_fetch(UA, url0):
        sys.exit("robots.txt disallows this client for the export path; download manually from the portal instead.")
    s = requests.Session()
    s.headers["User-Agent"] = UA
    for ed in EDITIONS:
        dest = OUT / f"core_{ed}.csv"
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"{ed}: already have {dest.name}")
            continue
        r = s.get(BASE, params={"search": "", "by": "all", "source": ed, "sort": "arank", "page": 1, "do": "Export"}, timeout=120)
        lines = r.text.count("\n")
        if r.status_code == 200 and lines > 50 and "," in r.text[:200]:
            dest.write_text(r.text)
            print(f"{ed}: {lines} rows -> {dest.relative_to(ROOT)}")
        else:
            print(f"{ed}: not available (HTTP {r.status_code}, {lines} lines) — skipped")
        time.sleep(5)


if __name__ == "__main__":
    main()
