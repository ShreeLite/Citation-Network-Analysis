"""Download Scimago (SJR) journal-rank exports 2016–2025 into data/external/scimago/.

scimagojr.com answers 403 to plain scripts; robots.txt allows us and the user confirmed
institutional permission, so the export is fetched through a real browser session
(Playwright) — one page view + one download per year, with a polite pause. Years already on
disk are skipped. If the browser route fails, the script prints the URLs to download by hand.
"""
from __future__ import annotations

import time

from common.config import EXTERNAL, cfg, setup_logging
from common.sources import web

log = setup_logging("00_scimago")
OUT = EXTERNAL / "scimago"
PAGE = "https://www.scimagojr.com/journalrank.php?year={y}"
EXPORT = "https://www.scimagojr.com/journalrank.php?year={y}&out=xls"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    years = [y for y in range(cfg()["years"]["start"], cfg()["years"]["end"]) if not (OUT / f"scimagojr_{y}.csv").exists()]
    if not years:
        print("Scimago: all years present")
        return
    if not web().allowed(PAGE.format(y=years[0])):
        raise SystemExit("robots.txt disallows scimagojr.com for us; download manually.")
    from playwright.sync_api import sync_playwright

    failed = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(user_agent=None, accept_downloads=True)  # Chromium's own UA
        page = ctx.new_page()
        for y in years:
            try:
                page.goto(PAGE.format(y=y), timeout=90000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                with page.expect_download(timeout=180000) as dl:
                    page.evaluate("u => { const a = document.createElement('a'); a.href = u; document.body.appendChild(a); a.click(); }",
                                  EXPORT.format(y=y))
                tmp = OUT / f"scimagojr_{y}.csv.part"
                dl.value.save_as(tmp)
                head = tmp.read_text(encoding="utf-8", errors="replace")[:300]
                if "Best Quartile" not in head:
                    raise RuntimeError(f"unexpected content: {head[:120]!r}")
                tmp.rename(OUT / f"scimagojr_{y}.csv")
                print(f"Scimago {y}: ok")
            except Exception as e:
                log.warning("Scimago %s failed: %s", y, e)
                failed.append(y)
            time.sleep(cfg()["rate_limits"]["web"] * 2)
        b.close()
    if failed:
        print("Could not fetch these years; download by hand into data/external/scimago/ as scimagojr_<year>.csv:")
        for y in failed:
            print("  ", EXPORT.format(y=y))


if __name__ == "__main__":
    main()
