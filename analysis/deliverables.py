"""Build deliverables/: the four official CSVs (exact names/columns), the formatted Excel
workbook, and group9_deliverables.zip."""
from __future__ import annotations

import json
import shutil
import zipfile

import pandas as pd

from common.config import DATA, DELIVERABLES, PROCESSED, QA, cfg, collection_date, setup_logging

log = setup_logging("deliverables")
SPEC_COLS = ["group", "institution", "author", "title", "year", "type", "journal_name", "issn", "doi", "citations",
             "quartile", "coauthor_institutes", "cites_indian_inst", "cited_by_indian_inst"]
EXCEL_MAX = 1_048_575
YP = cfg()["years"]["partial_year"]

DICTIONARY = [
    ("group", "group9_data", "Group number (9)."),
    ("institution", "group9_data", "IIIT-H or IIIT-D: the institute of the faculty member in `author`."),
    ("author", "group9_data", "Faculty member (one row per faculty author × paper; a paper with two of our faculty appears twice)."),
    ("title / year", "group9_data", f"Paper title and publication year (2016–2026; {YP} is partial)."),
    ("type", "group9_data", "journal or conference (DBLP record type wins for CS venues, then OpenAlex source type, Crossref type, IIIT-H portal)."),
    ("journal_name", "group9_data", "Canonical venue name (journal title, or normalised conference name); acronym in papers sheet."),
    ("issn", "group9_data", "All ISSNs known for the venue (print and electronic), from OpenAlex + Crossref."),
    ("doi", "group9_data", "DOI (lowercase). Missing for some conference papers; papers sheet has the OpenAlex ID."),
    ("citations", "group9_data", f"OpenAlex cited_by_count at collection date ({collection_date()}); Semantic Scholar count and max/mean in papers sheet."),
    ("quartile", "group9_data", "Scimago SJR best quartile across the journal's subject categories, for the paper's year (nearest available year if missing). Journals only."),
    ("coauthor_institutes", "group9_data", "Distinct institutions of all authors on the paper (OpenAlex authorships), ';'-separated; countries in papers.coauthor_countries."),
    ("cites_indian_inst", "group9_data", "TRUE if any referenced work has an Indian (country IN) institution other than the citing paper's own institute(s)."),
    ("cited_by_indian_inst", "group9_data", "TRUE if any citing work has an Indian institution other than the paper's own institute(s)."),
    ("source_doi / target_doi", "citation_network", "Citing (our paper) and cited work; OpenAlex ID used when the DOI is missing."),
    ("internal_edge", "citation_network", "TRUE when the cited work is also in our IIIT-H/IIIT-D main set."),
    ("weight", "authorship_network", "1/(n_authors−1) per shared paper; big_paper = more than 25 authors."),
    ("total_citations", "indian_connections", "Citations our institute's papers received from the partner (citing work × partner institution)."),
    ("citations_given_to_partner", "indian_connections", "References from our papers to works with the partner institution."),
    ("topic_jaccard", "indian_connections", "Jaccard of OpenAlex topic sets (our papers vs partner's 2016–2026 output); top 200 partners per institute."),
]


def autosize(ws, df: pd.DataFrame, wb) -> None:
    hdr = wb.add_format({"bold": True, "bg_color": "#1F2937", "font_color": "#FFFFFF", "text_wrap": True, "valign": "top"})
    for j, c in enumerate(df.columns):
        width = min(60, max(10, len(str(c)) + 2, int(df[c].astype(str).str.len().head(500).quantile(0.9)) + 2 if len(df) else 10))
        ws.set_column(j, j, width)
        ws.write(0, j, c, hdr)
    ws.freeze_panes(1, 0)
    if len(df):
        ws.autofilter(0, 0, len(df), len(df.columns) - 1)


def main() -> None:
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    mp = pd.read_parquet(PROCESSED / "main_papers.parquet")
    ml = pd.read_parquet(PROCESSED / "main_links.parquet")
    allp = pd.read_parquet(PROCESSED / "papers_enriched.parquet")
    links = pd.read_parquet(PROCESSED / "faculty_paper_links.parquet")
    name = roster.set_index("faculty_id").name.to_dict()

    # official data file: one row per (faculty author, paper)
    d = ml[["faculty_id", "paper_id", "institution"]].merge(mp, on="paper_id", how="inner")
    off = pd.DataFrame({
        "group": 9, "institution": d.institution, "author": d.faculty_id.map(name), "title": d.title, "year": d.year.astype(int),
        "type": d.type, "journal_name": d.journal_name, "issn": d.issn, "doi": d.doi, "citations": d.citations.fillna(0).astype(int),
        "quartile": d.quartile, "coauthor_institutes": d.coauthor_institutes,
        "cites_indian_inst": d.cites_indian_inst.map({True: "TRUE", False: "FALSE"}),
        "cited_by_indian_inst": d.cited_by_indian_inst.map({True: "TRUE", False: "FALSE"}),
    })
    assert list(off.columns) == SPEC_COLS, off.columns
    off = off.sort_values(["institution", "author", "year", "title"])
    DELIVERABLES.mkdir(exist_ok=True)
    # UTF-8 with BOM: Excel then decodes accented / Indic characters correctly
    off.to_csv(DELIVERABLES / "group9_data.csv", index=False, encoding="utf-8-sig")
    for f in ("citation_network.csv", "authorship_network.csv", "indian_connections.csv"):
        pd.read_csv(PROCESSED / f).to_csv(DELIVERABLES / f, index=False, encoding="utf-8-sig")

    # workbook
    sheets = {
        "papers": mp.drop(columns=[c for c in ("cluster",) if c in mp]),
        "faculty": roster,
        "faculty_paper_links": links.assign(faculty_name=links.faculty_id.map(name)),
        "citation_edges": pd.read_csv(PROCESSED / "citation_network.csv"),
        "authorship_edges": pd.read_csv(PROCESSED / "authorship_network.csv"),
        "indian_connections": pd.read_csv(PROCESSED / "indian_connections.csv"),
        "citation_flow_by_year": pd.read_csv(PROCESSED / "citation_flow_by_year.csv"),
        "pre_joining_papers": links[links.status.eq("pre_joining")].merge(allp[["paper_id", "title", "year", "type", "doi"]], on="paper_id")
                              .assign(faculty_name=lambda x: x.faculty_id.map(name)),
        "preprints": allp[allp.type.eq("preprint")],
        "qa_summary": pd.read_csv(PROCESSED / "qa_summary.csv") if (PROCESSED / "qa_summary.csv").exists() else pd.DataFrame(),
    }
    findings_dir = PROCESSED / "analysis"
    csv_only = []
    with pd.ExcelWriter(DELIVERABLES / "group9_full_dataset.xlsx", engine="xlsxwriter") as xw:
        wb = xw.book
        # README first
        readme = [["Group 9 — IIIT Hyderabad + IIIT Delhi research mapping (DPCN)"], [f"Collected: {collection_date()}. 2026 is a partial year."],
                  ["Sources: OpenAlex (primary), DBLP, Crossref, Semantic Scholar (keyless, best-effort), IIIT-H publications portal, institute faculty pages, Wayback Machine, Scimago SJR, CORE rankings."],
                  ["One command rebuilds everything: make all (see README.md). Provenance: papers.sources lists the sources of each paper."],
                  [""], ["Data dictionary"]]
        pd.DataFrame(readme).to_excel(xw, sheet_name="README", index=False, header=False)
        ws = xw.sheets["README"]
        ws.set_column(0, 0, 28)
        ws.set_column(1, 1, 22)
        ws.set_column(2, 2, 110)
        bold = wb.add_format({"bold": True})
        r0 = len(readme) + 1
        for k, (col, sheet, desc) in enumerate(DICTIONARY):
            ws.write(r0 + k, 0, col, bold)
            ws.write(r0 + k, 1, sheet)
            ws.write(r0 + k, 2, desc)
        notes_row = r0 + len(DICTIONARY) + 1
        for sname, df in sheets.items():
            if len(df) > EXCEL_MAX:
                csv_only.append(sname)
                df.to_csv(DELIVERABLES / f"{sname}.csv", index=False)
                continue
            df = df.copy()
            for c in df.columns:
                if df[c].map(lambda v: isinstance(v, (list, dict, set))).any():
                    df[c] = df[c].map(lambda v: "; ".join(map(str, v)) if isinstance(v, (list, set)) else json.dumps(v) if isinstance(v, dict) else v)
            df.to_excel(xw, sheet_name=sname[:31], index=False)
            autosize(xw.sheets[sname[:31]], df, wb)
        # findings: one table per finding, stacked on one sheet
        fws = wb.add_worksheet("findings")
        row = 0
        for f in sorted(findings_dir.glob("finding*.csv")):
            df = pd.read_csv(f)
            fws.write(row, 0, f.stem, wb.add_format({"bold": True, "font_size": 13}))
            row += 1
            for j, c in enumerate(df.columns):
                fws.write(row, j, c, bold)
            for i, rec in enumerate(df.head(2000).itertuples(index=False), start=1):
                for j, v in enumerate(rec):
                    fws.write(row + i, j, "" if pd.isna(v) else v)
            row += len(df.head(2000)) + 3
        if csv_only:
            ws.write(notes_row, 0, "CSV-only sheets (exceed Excel's 1,048,576-row limit): " + ", ".join(f"{s}.csv" for s in csv_only), bold)

    # zip
    zp = DELIVERABLES / "group9_deliverables.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in ["group9_data.csv", "citation_network.csv", "authorship_network.csv", "indian_connections.csv", "group9_full_dataset.xlsx"] + [f"{s}.csv" for s in csv_only]:
            z.write(DELIVERABLES / f, f)
        if (QA / "qa_report.md").exists():
            z.write(QA / "qa_report.md", "qa_report.md")
    print(f"deliverables: {len(off):,} rows in group9_data.csv; zip {zp} ({zp.stat().st_size/1e6:.1f} MB); csv-only: {csv_only or 'none'}")


if __name__ == "__main__":
    main()
