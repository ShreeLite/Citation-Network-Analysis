"""High-resolution PNGs for the ≤10-slide report -> report_figures/. Reads the site JSON so the
figures and the website always show the same numbers. Colours = validated reference palette
(IIIT-H blue, IIIT-D orange; journal aqua, conference violet)."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from common.config import FIGURES, SITE_DATA, cfg  # noqa: E402

C = {"IIIT-H": "#2a78d6", "IIIT-D": "#eb6834", "journal": "#1baf7a", "conference": "#4a3aa7", "ink": "#0b0b0b", "ink2": "#52514e",
     "muted": "#898781", "grid": "#e1e0d9", "surface": "#fcfcfb"}
INSTS = ["IIIT-H", "IIIT-D"]
YP = cfg()["years"]["partial_year"]

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": C["grid"], "axes.labelcolor": C["ink2"],
                     "xtick.color": C["muted"], "ytick.color": C["muted"], "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.8, "axes.axisbelow": True,
                     "figure.facecolor": C["surface"], "axes.facecolor": C["surface"], "savefig.dpi": 300, "legend.frameon": False})


def load(name):
    return json.loads((SITE_DATA / f"{name}.json").read_text())


def save(fig, name, title, caption):
    fig.suptitle(title, x=0.02, ha="left", fontsize=14, fontweight="bold", color=C["ink"])
    fig.text(0.02, 0.005, caption, fontsize=9, color=C["muted"], ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(FIGURES / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def trend(req):
    fig, ax = plt.subplots(figsize=(10, 4.6))
    years = list(range(cfg()["years"]["start"], cfg()["years"]["end"] + 1))
    w = 0.4
    for k, i in enumerate(INSTS):
        v = [sum(r["papers"] for r in req["trend"] if r["institution"] == i and r["year"] == y) for y in years]
        bars = ax.bar(np.array(years) + (k - 0.5) * w, v, w * 0.92, color=C[i], label=i)
        bars[-1].set_alpha(0.45)
        bars[-1].set_hatch("///")
    ax.set_ylabel("papers")
    ax.set_xticks(years)
    ax.legend(loc="upper left")
    save(fig, "01_publication_trend", "Publications per year", f"Journal + conference papers by core faculty, deduplicated across sources. {YP} is partial (hatched).")


def quality(req):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    q = {r["institution"]: r for r in req["quality"]}
    for ax, key, cats, sub in ((axes[0], "quartiles", ["Q1", "Q2", "Q3", "Q4"], "journals_with_quartile"), (axes[1], "core_ranks", ["A*", "A", "B", "C"], "conferences_with_core")):
        x = np.arange(len(cats))
        for k, i in enumerate(INSTS):
            n = max(1, q[i][sub])
            ax.bar(x + (k - 0.5) * 0.4, [100 * q[i][key].get(c, 0) / n for c in cats], 0.37, color=C[i], label=f"{i} (n={q[i][sub]})")
        ax.set_xticks(x, cats)
        ax.set_ylabel("% of ranked papers")
        ax.legend()
    axes[0].set_title("Journal quartile (Scimago)", loc="left", fontsize=11, color=C["ink2"])
    axes[1].set_title("Conference rank (CORE)", loc="left", fontsize=11, color=C["ink2"])
    save(fig, "02_venue_quality", "Venue quality: journals and conferences", "Shares among papers with a known rank; journals are a minority of IIIT output, so both panels are needed.")


def central_fig(cq):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ks = ["clustering", "modularity", "cross_unit_share"]
    x = np.arange(len(ks))
    for k, i in enumerate(INSTS):
        r = [cq[i]["null_model"]["ratio"].get(m) or 0 for m in ks]
        ax.bar(x + (k - 0.5) * 0.4, r, 0.37, color=C[i], label=f"{i} (NMI units↔communities = {cq[i]['nmi_units_vs_communities']:.2f})")
    ax.axhline(1, color=C["muted"], lw=1)
    ax.set_xticks(x, ["avg clustering", "modularity", "cross-unit share"])
    ax.set_ylabel("× degree-preserving random")
    ax.legend(loc="upper right")
    save(fig, "03_central_question", "Does the org chart shape who works with whom?", "Observed value ÷ mean over random rewirings that keep each person's number of co-authors. 1.0 = chance.")


def f1_fig(F):
    fig, ax = plt.subplots(figsize=(9, 5))
    for i in INSTS:
        s = [r for r in F["f1"]["scatter"] if r["institution"] == i]
        ax.scatter([r["degree"] for r in s], [r["betweenness"] for r in s], s=[60 if r["flagged"] else 22 for r in s], color=C[i],
                   edgecolors=[C["ink"] if r["flagged"] else C["surface"] for r in s], linewidths=1.5, alpha=0.85, label=i)
        for r in s:
            if r["flagged"]:
                ax.annotate(r["name"], (r["degree"], r["betweenness"]), fontsize=8, color=C["ink2"], xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("degree (co-authors within institute)")
    ax.set_ylabel("betweenness")
    ax.legend()
    save(fig, "04_finding1_hidden_glue", "Finding 1 · The hidden glue", "Outlined: top-15% betweenness with below-median degree. Remove them and the largest collaborating group shrinks.")


def f3_fig(F):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for r in [r for r in F["f3"]["summary"] if r["unit"] == "All units"]:
        ax.plot([1, 2, 3], [r["median_deg_y1"], r["median_deg_y2"], r["median_deg_y3"]], marker="o", lw=2, color=C[r["institution"]],
                label=f"{r['institution']} (n={r['n']}; {100 * r['share_zero_after_3y']:.0f}% still at 0)")
    ax.set_xticks([1, 2, 3], ["Year 1", "Year 2", "Year 3"])
    ax.set_ylabel("median internal co-authors")
    ax.legend()
    save(fig, "05_finding3_new_joiners", "Finding 3 · How long new faculty take to fit in", "Faculty who joined 2016+; cumulative distinct co-authors among same-institute core faculty.")


def f6_fig(F):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for i in INSTS:
        rows = [r for r in F["f6"]["rows"] if r["institution"] == i and r["year"] != "all"]
        ax.plot([r["year"] for r in rows], [100 * (r["top10_share_citations"] or 0) for r in rows], marker="o", lw=2, color=C[i], label=i)
    ax.set_ylabel("% of citations held by top 10% of faculty")
    ax.set_ylim(0, 100)
    ax.legend()
    save(fig, "06_finding6_concentration", "Finding 6 · Concentration risk", f"By publication year; recent years' citations are still accruing; {YP} partial.")


def f7_fig(F):
    fig, ax = plt.subplots(figsize=(9, 5))
    for i in INSTS:
        p = F["f7"].get(i, {}).get("partners", [])
        ax.scatter([r["shared_papers"] + 1 for r in p], [r["total_citations"] + 1 for r in p], s=26, color=C[i], alpha=0.8,
                   edgecolors=[C["ink"] if r.get("cites_us_not_collab") else C["surface"] for r in p], linewidths=1.2, label=i)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("co-authored papers + 1")
    ax.set_ylabel("citations to us + 1")
    ax.legend()
    save(fig, "07_finding7_cites_not_collab", "Finding 7 · Who cites us but never works with us?", "Each dot is an Indian institution; outlined = top 10% by citations to us with ≤ 1 joint paper.")


def f5_fig(F):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    r = F["f5"]["by_year"]
    ax.plot([x["year"] for x in r], [x["cross_median"] for x in r], marker="o", lw=2, color=C["conference"], label="cross-unit")
    ax.plot([x["year"] for x in r], [x["within_median"] for x in r], marker="o", lw=2, color=C["journal"], label="within-unit")
    ax.set_ylabel("median citations")
    ax.legend()
    save(fig, "08_finding5_bridging", "Finding 5 · Does bridging pay off?", "Median citations of papers from the same year; single-faculty papers excluded.")


def main():
    req, F, cq = load("required"), load("findings"), load("central")
    for fn in (lambda: trend(req), lambda: quality(req), lambda: central_fig(cq), lambda: f1_fig(F), lambda: f3_fig(F),
               lambda: f5_fig(F), lambda: f6_fig(F), lambda: f7_fig(F)):
        fn()
    print("figures ->", FIGURES, sorted(p.name for p in FIGURES.glob("*.png")))


if __name__ == "__main__":
    main()
