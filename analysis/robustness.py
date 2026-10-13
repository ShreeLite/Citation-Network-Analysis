"""Robustness: re-run the headline results (a) without large-team papers (> 25 authors) and
(b) with preprints included, and flag any finding whose direction flips.
-> qa/robustness.md, data/processed/analysis/robustness.json"""
from __future__ import annotations

import itertools
import json

import pandas as pd

from analysis import run_all as R
from common.config import PROCESSED, QA, cfg

BIG = cfg()["flags"]["big_paper_authors"]


def edges_from_links(mp: pd.DataFrame, ml: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    """Faculty co-authorship edges rebuilt from links (so variants with other paper sets work)."""
    inst = roster.set_index("faculty_id").institution.to_dict()
    nm = roster.set_index("faculty_id").name.to_dict()
    meta = mp.set_index("paper_id")
    rows = []
    for pid, g in ml[ml.paper_id.isin(meta.index)].groupby("paper_id"):
        facs = sorted(set(g.faculty_id))
        n = int(meta.at[pid, "n_authors"]) if pd.notna(meta.at[pid, "n_authors"]) else len(facs)
        for a, b in itertools.combinations(facs, 2):
            rows.append({"author_a": nm[a], "author_b": nm[b], "paper_doi": meta.at[pid, "doi"] or pid, "inst_a": inst[a], "inst_b": inst[b],
                         "year": int(meta.at[pid, "year"]), "faculty_id_a": a, "faculty_id_b": b, "cross_institution": inst[a] != inst[b],
                         "n_authors": n, "weight": 1 / max(1, n - 1), "big_paper": n > BIG})
    return pd.DataFrame(rows)


def headline(core, mp, ml, an, ic, edges, insts) -> dict:
    G_all, G_inst = R.coauthor_graphs(core, an)
    cq = R.central_question(core, G_inst)
    f1 = R.finding1(core, G_inst)
    f3 = R.finding3(core, ml, mp, an)
    f5 = R.finding5(core, ml, mp)
    f6 = R.finding6(core, ml, mp, G_inst)
    f7 = R.finding7(ic, edges, mp, insts)
    p = f5["pooled_year_normalised"]
    ratio = (p.get("cross-unit", {}).get("median_norm_citations") or float("nan")) / (p.get("within-unit", {}).get("median_norm_citations") or float("nan"))
    out = {"papers": len(mp)}
    for i in R.INSTS:
        out[f"{i} NMI"] = cq[i]["nmi_units_vs_communities"]
        out[f"{i} cross-unit share"] = cq[i]["cross_unit_share_links"]
        out[f"{i} cross-unit z"] = cq[i]["null_model"]["z"].get("cross_unit_share")
        out[f"{i} hidden-glue flagged"] = f1["n_flagged"][i]
        z3 = [r for r in f3["summary"] if r["institution"] == i and r["unit"] == "All units"]
        out[f"{i} share at 0 after 3y"] = z3[0]["share_zero_after_3y"] if z3 else None
        all6 = [r for r in f6["rows"] if r["institution"] == i and r["year"] == "all"]
        out[f"{i} top10 citation share"] = all6[0]["top10_share_citations"] if all6 else None
        out[f"{i} cites-us-not-collab"] = len(f7.get(i, {}).get("flagged", []))
    out["F5 cross/within ratio"] = ratio
    return out


def main() -> None:
    roster, core, allp, links, mp, ml, an, ic, fy, edges, cn, insts = R.load()
    ml = ml[ml.faculty_id.isin(core.faculty_id)]
    base = headline(core, mp, ml, an, ic, edges, insts)
    # (a) without large-team papers
    small = mp[mp.n_authors.fillna(0) <= BIG]
    va = headline(core, small, ml[ml.paper_id.isin(small.paper_id)], an[~an.big_paper.astype(bool)], ic, edges, insts)
    # (b) with preprints
    pre = R.effective_quartile(R.unpublished_preprints(allp, mp, links).copy())
    pre["our_institutions"] = pre.paper_id.map(links[links.in_main_set].groupby("paper_id").institution.apply(lambda s: ";".join(sorted(set(s)))))
    mp_b = pd.concat([mp, pre], ignore_index=True)
    ml_b = pd.concat([ml, links[links.in_main_set & links.paper_id.isin(pre.paper_id) & links.faculty_id.isin(core.faculty_id)]])
    vb = headline(core, mp_b, ml_b, edges_from_links(mp_b, ml_b, roster), ic, edges, insts)

    def flips(k):
        b, x = base.get(k), [va.get(k), vb.get(k)]
        if b is None or any(v is None for v in x) or isinstance(b, int):
            return ""
        if "ratio" in k:
            return "FLIPS" if any((v > 1) != (b > 1) for v in x) else ""
        if " z" in k:
            return "FLIPS" if any((v < -2) != (b < -2) or (v > 2) != (b > 2) for v in x) else ""
        return "SHIFT > 25%" if any(b and abs(v - b) / abs(b) > 0.25 for v in x) else ""
    rows = [{"metric": k, "baseline": base[k], "no >25-author papers": va.get(k), "with preprints": vb.get(k), "robustness": flips(k)} for k in base]
    df = pd.DataFrame(rows)
    (PROCESSED / "analysis" / "robustness.json").write_text(json.dumps(R.clean(rows), indent=1))
    txt = ["# Robustness checks", "", "Headline numbers re-computed (a) without papers that have more than 25 authors and (b) with arXiv-only preprints included.",
           "‘FLIPS’ marks a result whose direction changes (e.g. ratio crosses 1, z-score crosses ±2); such findings are reported as fragile.", "",
           df.to_markdown(index=False, floatfmt=".3f")]
    (QA / "robustness.md").write_text("\n".join(txt))
    print("\n".join(txt))


if __name__ == "__main__":
    main()
