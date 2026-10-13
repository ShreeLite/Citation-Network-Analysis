"""Fill the RESULTS block of README.md with the final numbers (counts, coverage, QA, findings)."""
from __future__ import annotations

import json
import re

import pandas as pd

from common.config import DATA, DELIVERABLES, PROCESSED, ROOT, SITE_DATA, collection_date


def pct(x):
    return "—" if x is None or x != x else f"{100 * x:.0f}%"


def main() -> None:
    r = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    mp = pd.read_parquet(PROCESSED / "main_papers.parquet")
    qa = dict(pd.read_csv(PROCESSED / "qa_summary.csv").values) if (PROCESSED / "qa_summary.csv").exists() else {}
    meta = json.loads((SITE_DATA / "meta.json").read_text())
    F = json.loads((SITE_DATA / "findings.json").read_text())
    C = json.loads((SITE_DATA / "central.json").read_text())
    core = r[r.is_core.eq("True")]
    zp = DELIVERABLES / "group9_deliverables.zip"
    lines = ["## Results at a glance", "",
             f"Collected {collection_date()} (2026 partial).", "",
             "| | IIIT-H | IIIT-D |", "|---|---|---|"]
    for label, f in [("Core faculty (current)", lambda i: (core.institution.eq(i) & core.status.eq("current")).sum()),
                     ("Former core faculty (2016–2026)", lambda i: (core.institution.eq(i) & core.status.eq("former")).sum()),
                     ("Papers (journal + conference)", lambda i: mp.our_institutions.str.contains(i).sum()),
                     ("Conference share", lambda i: pct(mp[mp.our_institutions.str.contains(i)].type.eq("conference").mean())),
                     ("NMI official units vs communities", lambda i: f"{C[i]['nmi_units_vs_communities']:.2f}"),
                     ("Cross-unit share of collaborations", lambda i: pct(C[i]["cross_unit_share_links"]))]:
        lines.append(f"| {label} | {f('IIIT-H')} | {f('IIIT-D')} |")
    lines += ["", "**Quality checks:** " + "; ".join(f"{k.replace('_', ' ')} = {v}" for k, v in qa.items() if any(s in k for s in ("dblp", "audit", "dup", "self", "own_partner", "filled_doi", "quartile", "CORE"))),
              f"Quartiles from: {meta.get('quartile_source')}.", "",
              f"**Deliverables:** `{zp.relative_to(ROOT)}` ({zp.stat().st_size / 1e6:.1f} MB) · website `site/dist/index.html`.", "",
              "QA reports: `qa/checkpoint1.md`, `qa/checkpoint2.md`, `qa/qa_report.md` (checkpoint 3), `qa/robustness.md`, `qa/findings_handcheck.md`, `qa/site_check.md`."]
    readme = (ROOT / "README.md").read_text()
    block = "<!-- RESULTS:START -->\n" + "\n".join(lines) + "\n<!-- RESULTS:END -->"
    readme = re.sub(r"<!-- RESULTS:START -->.*?<!-- RESULTS:END -->", block, readme, flags=re.S)
    (ROOT / "README.md").write_text(readme)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
