"""Website checks (qa/sanity_checklist.md, 'Website') -> qa/site_check.md + screenshots.

Opens site/dist/index.html from file:// with networking disabled (offline, like an emailed zip
on another laptop), at desktop and phone widths, and checks: every tab renders without console
errors, no horizontal scroll on a phone, filters add up (IIIT-H + IIIT-D − joint = both),
2026 is marked partial, and headline numbers match the workbook.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

sys.path.insert(0, ".")
from common.config import DELIVERABLES, QA, ROOT  # noqa: E402

DIST = ROOT / "site" / "dist" / "index.html"
TABS = ["overview", "publications", "faculty", "venues", "areas", "citations", "collaboration", "central", "findings", "india", "methods"]


def kpi(page, label: str) -> str:
    return page.locator(f"text={label}").first.locator("xpath=..").inner_text()


def num(text: str) -> int:
    m = re.search(r"([\d,]+)", text.replace(" ", ""))
    return int(m.group(1).replace(",", "")) if m else -1


def main() -> None:
    url = DIST.as_uri()
    out, shots = [], QA / "site_screens"
    shots.mkdir(exist_ok=True)
    wb = pd.read_csv(DELIVERABLES / "group9_data.csv", encoding="utf-8-sig")
    papers_wb = pd.read_excel(DELIVERABLES / "group9_full_dataset.xlsx", sheet_name="papers")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for w, h, tag in ((1440, 900, "desktop"), (390, 844, "phone")):
            ctx = b.new_context(viewport={"width": w, "height": h}, offline=True)
            pg = ctx.new_page()
            errs = []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append(str(e)))
            widths = {}
            for t in TABS:
                pg.goto(f"{url}#/{t}")
                pg.wait_for_timeout(1500 if t in ("citations", "collaboration") else 700)
                widths[t] = pg.evaluate("document.documentElement.scrollWidth")
                pg.screenshot(path=str(shots / f"{tag}_{t}.png"), full_page=False)
            over = {t: v for t, v in widths.items() if v > w + 1}
            out.append(f"- **{tag} ({w}px, offline)**: console errors {len(errs)}{' — ' + '; '.join(errs[:3]) if errs else ''}; "
                       f"horizontal overflow on {list(over) or 'no tab'}")
            ctx.close()
        # filters add up + headline numbers (desktop, offline)
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, offline=True)
        pg = ctx.new_page()
        counts = {}
        for inst in ("both", "IIIT-H", "IIIT-D"):
            pg.goto(f"{url}#/overview?inst={inst}" if inst != "both" else f"{url}#/overview")
            pg.wait_for_timeout(700)
            counts[inst] = num(kpi(pg, "Papers"))
        joint = int(papers_wb.our_institutions.astype(str).str.contains(";").sum())
        ok = counts["IIIT-H"] + counts["IIIT-D"] - joint == counts["both"]
        out.append(f"- **Filters add up**: IIIT-H {counts['IIIT-H']} + IIIT-D {counts['IIIT-D']} − joint {joint} = {counts['IIIT-H'] + counts['IIIT-D'] - joint} "
                   f"vs both {counts['both']} → {'✓' if ok else '✗'}")
        wb_papers = len(papers_wb)
        out.append(f"- **Headline vs workbook**: site papers (both, journal+conference) {counts['both']} vs workbook papers sheet {wb_papers} "
                   f"→ {'✓' if counts['both'] == wb_papers else '✗'}; official file rows {len(wb):,}")
        pg.goto(f"{url}#/overview")
        pg.wait_for_timeout(700)
        partial = pg.locator("text=2026 = partial year").count() > 0
        opt = pg.locator("option", has_text="2026 (partial)").count() > 0
        out.append(f"- **2026 marked partial**: chip {'✓' if partial else '✗'}, year selector {'✓' if opt else '✗'}")
        zip_link = pg.locator("a[href='./group9_deliverables.zip']").count() > 0 and (DIST.parent / "group9_deliverables.zip").exists()
        out.append(f"- **Download data** link present and zip next to index.html: {'✓' if zip_link else '✗'}")
        size = DIST.stat().st_size / 1e6
        out.append(f"- **Single self-contained file**: {DIST.name} {size:.1f} MB (no external requests needed; verified with networking disabled)")
        b.close()
    txt = ["# Website checks", "", *out, "", f"Screenshots: `qa/site_screens/` ({len(list(shots.glob('*.png')))} files)."]
    (QA / "site_check.md").write_text("\n".join(txt))
    print("\n".join(txt))


if __name__ == "__main__":
    main()
