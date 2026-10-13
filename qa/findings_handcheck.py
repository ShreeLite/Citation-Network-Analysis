"""Hand-check one number per finding by recomputing it ONLY from the published workbook
(deliverables/group9_full_dataset.xlsx), with code independent of analysis/run_all.py.
-> qa/findings_handcheck.md"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from common.config import DELIVERABLES, QA, SITE_DATA  # noqa: E402

XL = DELIVERABLES / "group9_full_dataset.xlsx"


def main() -> None:
    fac = pd.read_excel(XL, sheet_name="faculty", dtype=str).fillna("")
    papers = pd.read_excel(XL, sheet_name="papers")
    links = pd.read_excel(XL, sheet_name="faculty_paper_links")
    edges = pd.read_excel(XL, sheet_name="authorship_edges")
    ic = pd.read_excel(XL, sheet_name="indian_connections")
    F = json.loads((SITE_DATA / "findings.json").read_text())
    core = fac[fac.is_core.str.lower().eq("true")]
    main = links[links.in_main_set.astype(str).str.lower().eq("true") & links.faculty_id.isin(core.faculty_id) & links.paper_id.isin(papers.paper_id)]
    rows = []

    def G_of(inst):
        G = nx.Graph()
        G.add_nodes_from(core[core.institution == inst].faculty_id)
        for e in edges.itertuples():
            if e.inst_a == inst and e.inst_b == inst:
                G.add_edge(e.faculty_id_a, e.faculty_id_b)
        return G

    # F1: largest-component drop for the headline person
    hp = F["f1"].get("headline_person")
    if hp:
        G = G_of(hp["institution"])
        before = max(len(c) for c in nx.connected_components(G))
        H = G.copy()
        H.remove_node(hp["faculty_id"])
        after = max(len(c) for c in nx.connected_components(H))
        rows.append(("F1 LCC drop when removing " + hp["name"], hp["lcc_drop"], before - 1 - after))
    # F2: articulation points in the unit with most of them
    pu = max(F["f2"]["per_unit"], key=lambda r: r["articulation_points"])
    G = G_of(pu["institution"]).subgraph(core[(core.institution == pu["institution"]) & (core.unit.replace("", "Unassigned") == pu["unit"])].faculty_id)
    rows.append((f"F2 articulation points in {pu['unit']} ({pu['institution']})", pu["articulation_points"], len(list(nx.articulation_points(G)))))
    # F3: share still at zero internal co-authors after 3 years (IIIT-D, all units)
    s3 = [r for r in F["f3"]["summary"] if r["unit"] == "All units"]
    if s3:
        r0 = s3[0]
        inst = r0["institution"]
        ys = edges[(edges.inst_a == inst) & (edges.inst_b == inst)]
        zero = tot = 0
        for f in core[core.institution == inst].itertuples():
            jy = pd.to_numeric(f.joining_year, errors="coerce")
            if pd.isna(jy) or jy < 2016 or jy + 2 > 2025:
                continue
            tot += 1
            e = ys[((ys.faculty_id_a == f.faculty_id) | (ys.faculty_id_b == f.faculty_id)) & (ys.year <= jy + 2)]
            zero += e.empty
        rows.append((f"F3 share at zero after 3 years ({inst})", round(r0["share_zero_after_3y"], 3), round(zero / tot, 3) if tot else None))
    # F4: topic Jaccard of the top missed pair
    if F["f4"]["pairs"]:
        p = F["f4"]["pairs"][0]
        tp = main.merge(papers[["paper_id", "topic_id"]], on="paper_id")
        def topics(fid):
            c = tp[tp.faculty_id == fid].topic_id.dropna().value_counts()
            n = tp[tp.faculty_id == fid].paper_id.nunique()
            return set(c[c >= 2].index) if n >= 5 else set(c.index)
        a, b = topics(p["faculty_id_a"]), topics(p["faculty_id_b"])
        rows.append((f"F4 topic Jaccard {p['faculty_a']} – {p['faculty_b']}", p["topic_jaccard"], round(len(a & b) / len(a | b), 3) if a | b else None))
    # F5: pooled year-normalised median ratio cross/within
    unit = core.set_index("faculty_id").unit.replace("", "Unassigned").to_dict()
    inst = core.set_index("faculty_id").institution.to_dict()
    lab = {}
    for pid, g in main.groupby("paper_id"):
        fs = set(g.faculty_id)
        if len(fs) < 2:
            continue
        lab[pid] = "cross" if len({(inst[f], unit[f]) for f in fs}) > 1 else "within"
    pp = papers[papers.paper_id.isin(main.paper_id) & (papers.year < 2026)].copy()
    pp["citations"] = pp.citations.fillna(0)
    allp = papers[papers.paper_id.isin(main.paper_id)].copy()
    allp["citations"] = allp.citations.fillna(0)
    med = allp.groupby("year").citations.median().replace(0, np.nan)
    pp["norm"] = pp.citations / pp.year.map(med)
    pp["lab"] = pp.paper_id.map(lab)
    m = pp.dropna(subset=["lab"]).groupby("lab").norm.median()
    pooled = F["f5"]["pooled_year_normalised"]
    site = pooled.get("cross-unit", {}).get("median_norm_citations", np.nan) / pooled.get("within-unit", {}).get("median_norm_citations", np.nan)
    rows.append(("F5 cross/within year-normalised median ratio", round(site, 3), round(m.get("cross", np.nan) / m.get("within", np.nan), 3)))
    # F6: top-10% citation share, all years, IIIT-H
    r6 = [r for r in F["f6"]["rows"] if r["institution"] == "IIIT-H" and r["year"] == "all"][0]
    cit = papers.set_index("paper_id").citations.fillna(0)
    hc = core[core.institution == "IIIT-H"].faculty_id
    per = main[main.faculty_id.isin(hc)].assign(c=lambda x: x.paper_id.map(cit)).groupby("faculty_id").c.sum().reindex(hc, fill_value=0).sort_values(ascending=False)
    k = int(np.ceil(0.1 * len(per)))
    rows.append(("F6 top-10% citation share, IIIT-H, 2016–2026", round(r6["top10_share_citations"], 3), round(per.iloc[:k].sum() / per.sum(), 3)))
    # F7: number of 'cites us but rarely co-authors' institutes (IIIT-D)
    sub = ic[ic.your_inst == "IIIT-D"]
    thr = sub.total_citations.quantile(0.9)
    n7 = int(((sub.total_citations >= thr) & (sub.shared_papers <= 1)).sum())
    rows.append(("F7 MoU-target institutes, IIIT-D", len(F["f7"].get("IIIT-D", {}).get("flagged", [])), n7))

    df = pd.DataFrame(rows, columns=["number", "analysis pipeline", "recomputed from workbook"])
    df["match"] = [("✓" if (a == b or (isinstance(a, float) and b is not None and abs(a - b) < 0.006)) else "✗") for a, b in zip(df.iloc[:, 1], df.iloc[:, 2])]
    txt = ["# Hand-check: one number per finding, recomputed from the workbook", "",
           "Each number is recomputed with separate code that reads only `deliverables/group9_full_dataset.xlsx`.", "", df.to_markdown(index=False)]
    (QA / "findings_handcheck.md").write_text("\n".join(txt))
    print("\n".join(txt))


if __name__ == "__main__":
    main()
