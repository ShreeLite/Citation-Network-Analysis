"""Analysis: required metrics, central question, seven findings, null models.
Writes site/src/data/*.json, data/processed/analysis/*.csv (findings tables) and PNG figures.

Analytic choices (also exported to the Methods tab):
  * nodes = core faculty (Assistant/Associate/Full Professor, current + verified former);
  * main paper set = journal + conference papers 2016–2026 within tenure or institute-affiliated
    (preprints only when config flags.include_preprints is true);
  * co-authorship edge weight = Σ 1/(n_authors − 1); degree/betweenness use the unweighted graph;
  * communities = Louvain (networkx, seed 42) on the weighted within-institute faculty graph;
  * null model = degree-preserving double-edge swaps (≥100 samples, config thresholds.null_model_samples);
  * h-index (dataset) uses OpenAlex citations of main-set papers; lifetime h from OpenAlex summary_stats.
"""
from __future__ import annotations

import gzip
import itertools
import json
import math
from collections import Counter, defaultdict

import networkx as nx
import numpy as np
import pandas as pd

from analysis import graphs as g
from common.config import DATA, PROCESSED, SITE_DATA, cfg, collection_date, setup_logging
from common.sources import short_id

log = setup_logging("analysis")
Y0, Y1, YP = cfg()["years"]["start"], cfg()["years"]["end"], cfg()["years"]["partial_year"]
TH = cfg()["thresholds"]
OUT = PROCESSED / "analysis"
OUT.mkdir(exist_ok=True)
INSTS = ["IIIT-H", "IIIT-D"]


def unpublished_preprints(allp: pd.DataFrame, mp: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """arXiv-only works that are not just an earlier version of a main-set paper (identical
    normalised title — usually the arXiv version predates publication by > 2 years)."""
    from common.titles import normalise_title
    published = set(mp.title.map(normalise_title))
    pre = allp[allp.type.eq("preprint") & allp.paper_id.isin(links[links.in_main_set].paper_id)]
    return pre[~pre.title.map(normalise_title).isin(published)]


def h_index(cites) -> int:
    c = sorted((int(x) for x in cites if pd.notna(x)), reverse=True)
    return sum(1 for i, v in enumerate(c, 1) if v >= i)


def clean(o):
    """JSON-safe: NaN -> None, numpy -> python."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if (o is None or math.isnan(o) or math.isinf(o)) else round(float(o), 6)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def dump(name: str, obj) -> None:
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    (SITE_DATA / f"{name}.json").write_text(json.dumps(clean(obj), separators=(",", ":"), ensure_ascii=False))


# ---------------------------------------------------------------------------- load
QUARTILE_SOURCE = "scimago_sjr"


def effective_quartile(df: pd.DataFrame) -> pd.DataFrame:
    """Use Scimago SJR quartiles when they exist; otherwise the labelled OpenAlex proxy."""
    global QUARTILE_SOURCE
    if df.get("quartile", pd.Series(dtype=str)).fillna("").ne("").any():
        QUARTILE_SOURCE = "scimago_sjr"
    elif "quartile_proxy_openalex" in df:
        QUARTILE_SOURCE = "openalex_proxy"
        df = df.assign(quartile=df.quartile_proxy_openalex.fillna(""))
    return df


def load():
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    allp = pd.read_parquet(PROCESSED / "papers_enriched.parquet")
    links = pd.read_parquet(PROCESSED / "faculty_paper_links.parquet")
    mp = effective_quartile(pd.read_parquet(PROCESSED / "main_papers.parquet"))
    ml = pd.read_parquet(PROCESSED / "main_links.parquet")
    an = pd.read_csv(PROCESSED / "authorship_network.csv")
    ic = pd.read_csv(PROCESSED / "indian_connections.csv")
    fy = pd.read_csv(PROCESSED / "citation_flow_by_year.csv")
    edges = pd.read_parquet(PROCESSED / "citing_indian_edges.parquet")
    cn = pd.read_csv(PROCESSED / "citation_network.csv")
    insts = json.loads((PROCESSED / "institutions.json").read_text())
    core = roster[roster.is_core.eq("True")].copy()
    core["unit"] = core.unit.replace("", "Unassigned")
    return roster, core, allp, links, mp, ml, an, ic, fy, edges, cn, insts


# ---------------------------------------------------------------------------- required
def required_metrics(core, mp, ml, cn, roster):
    R = {}
    mp = mp.copy()
    mp["year"] = mp.year.astype(int)
    pi = mp.our_institutions.str.split(";")
    # trends
    rows = []
    for inst in INSTS:
        sub = mp[pi.map(lambda x: inst in x)]
        for (y, t), n in sub.groupby(["year", "type"]).size().items():
            rows.append({"institution": inst, "year": y, "type": t, "papers": n, "partial": y == YP})
    R["trend"] = rows
    # quality: Q1 share and CORE A*/A share
    q = []
    for inst in INSTS:
        sub = mp[pi.map(lambda x: inst in x)]
        j, c = sub[sub.type == "journal"], sub[sub.type == "conference"]
        jq, cr = j[j.quartile.ne("")], c[c.core_rank.isin(["A*", "A", "B", "C"])]
        q.append({"institution": inst, "journals": len(j), "journals_with_quartile": len(jq),
                  "q1_share_of_ranked": (jq.quartile == "Q1").mean() if len(jq) else None,
                  "q1_share_of_all_journals": (j.quartile == "Q1").mean() if len(j) else None,
                  "quartiles": jq.quartile.value_counts().to_dict(),
                  "conferences": len(c), "conferences_with_core": len(cr),
                  "core_astar_a_share_of_ranked": cr.core_rank.isin(["A*", "A"]).mean() if len(cr) else None,
                  "core_astar_a_share_of_all_conf": c.core_rank.isin(["A*", "A"]).mean() if len(c) else None,
                  "core_ranks": cr.core_rank.value_counts().to_dict(),
                  "journal_share": len(j) / max(1, len(j) + len(c))})
    R["quality"] = q
    # faculty performance
    cit = mp.set_index("paper_id").citations
    perf = []
    for f in core.itertuples():
        pids = ml[ml.faculty_id == f.faculty_id].paper_id.unique()
        sub = mp[mp.paper_id.isin(pids)]
        venues = sub.acronym.where(sub.acronym.fillna("").ne(""), sub.journal_name).value_counts()
        perf.append({"faculty_id": f.faculty_id, "name": f.name, "institution": f.institution, "unit": f.unit,
                     "units_secondary": f.units_secondary, "designation": f.designation, "status": f.status,
                     "joining_year": f.joining_year, "papers": len(sub), "journal": int((sub.type == "journal").sum()),
                     "conference": int((sub.type == "conference").sum()), "citations": int(cit.reindex(pids).fillna(0).sum()),
                     "h_index_dataset": h_index(sub.citations), "h_index_lifetime": pd.to_numeric(f.h_index_lifetime_openalex, errors="coerce") if "h_index_lifetime_openalex" in core else None,
                     "top_venue": venues.index[0] if len(venues) else "", "q1": int((sub.quartile == "Q1").sum()),
                     "core_astar_a": int(sub.core_rank.isin(["A*", "A"]).sum()),
                     "per_year": sub.groupby("year").size().to_dict(),
                     "fields": sub.field.value_counts().head(5).to_dict(),
                     "venues": venues.head(8).to_dict()})
    R["faculty"] = perf
    # top venues & cited
    tv = {}
    for inst in INSTS:
        sub = mp[pi.map(lambda x: inst in x)]
        name = sub.acronym.where(sub.acronym.fillna("").ne(""), sub.journal_name)
        tv[inst] = {t: sub[sub.type == t].assign(v=name).groupby("v").agg(papers=("paper_id", "size"), citations=("citations", "sum"))
                    .sort_values("papers", ascending=False).head(5).reset_index().to_dict("records") for t in ("journal", "conference")}
    R["top_venues"] = tv
    R["top_cited"] = {inst: mp[pi.map(lambda x: inst in x)].sort_values("citations", ascending=False).head(10)
                      [["title", "journal_name", "acronym", "year", "citations", "doi", "type"]].to_dict("records") for inst in INSTS + ["both"]}
    R["top_cited"]["both"] = mp.sort_values("citations", ascending=False).head(10)[["title", "journal_name", "acronym", "year", "citations", "doi", "type", "our_institutions"]].to_dict("records")
    # research areas
    ra = []
    for inst in INSTS:
        sub = mp[pi.map(lambda x: inst in x)]
        for (fl, sf), n in sub.groupby(["field", "subfield"]).size().items():
            ra.append({"institution": inst, "field": fl or "Unknown", "subfield": sf or "Unknown", "papers": n})
    R["areas"] = ra
    unit_of = core.set_index("faculty_id").unit.to_dict()
    lk = ml.merge(mp[["paper_id", "field"]], on="paper_id")
    lk["unit"] = lk.faculty_id.map(unit_of)
    R["unit_fields"] = lk.groupby(["institution", "unit", "field"]).paper_id.nunique().reset_index(name="papers").to_dict("records")

    # citation network (within corpus)
    internal = cn[cn.internal_edge.astype(str).eq("True")]
    CG = nx.DiGraph()
    CG.add_nodes_from(mp.openalex_id.dropna())
    CG.add_edges_from(zip(internal.source_openalex_id, internal.target_openalex_id))
    pr = nx.pagerank(CG) if CG.number_of_edges() else {}
    indeg = dict(CG.in_degree())
    meta = mp.set_index("openalex_id")
    top_pr = sorted(pr.items(), key=lambda kv: -kv[1])[:10]
    R["citation_network"] = {
        "nodes": CG.number_of_nodes(), "edges": CG.number_of_edges(),
        "pagerank_top10": [{"openalex_id": k, "pagerank": v, "in_degree": indeg.get(k, 0), "title": meta.at[k, "title"],
                            "year": int(meta.at[k, "year"]), "venue": meta.at[k, "acronym"] or meta.at[k, "journal_name"],
                            "institution": meta.at[k, "our_institutions"], "doi": meta.at[k, "doi"]} for k, v in top_pr],
        "in_degree_distribution": sorted(Counter(indeg.values()).items()),
        "cross_institute_flow": internal.groupby(["source_inst", "target_inst"]).size().reset_index(name="edges").to_dict("records"),
        "external_edges": int(len(cn) - len(internal)),
    }
    # graph sample for the site: top 600 by PageRank with edges among them
    keep = {k for k, _ in sorted(pr.items(), key=lambda kv: -kv[1])[:600]}
    R["citation_graph"] = {
        "nodes": [{"id": k, "pr": pr[k], "indeg": indeg.get(k, 0), "inst": meta.at[k, "our_institutions"], "year": int(meta.at[k, "year"]),
                   "title": meta.at[k, "title"], "venue": meta.at[k, "acronym"] or meta.at[k, "journal_name"]} for k in keep],
        "edges": [[a, b] for a, b in CG.edges() if a in keep and b in keep]}
    return R


# ---------------------------------------------------------------------------- co-authorship
def coauthor_graphs(core, an):
    nodes = {f.faculty_id: {"name": f.name, "institution": f.institution, "unit": f.unit} for f in core.itertuples()}
    E = [(r.faculty_id_a, r.faculty_id_b, r.weight, r.paper_doi) for r in an.itertuples()]
    G_all = g.faculty_graph(nodes, E)
    G_inst = {i: G_all.subgraph([n for n, d in G_all.nodes(data=True) if d["institution"] == i]).copy() for i in INSTS}
    return G_all, G_inst


def collaboration_metrics(core, G_all, G_inst, an):
    bet_all = nx.betweenness_centrality(G_all, normalized=True)
    out = {}
    for f in core.itertuples():
        n = f.faculty_id
        Gi = G_inst[f.institution]
        out[n] = {"degree": G_all.degree(n), "degree_internal": Gi.degree(n), "weighted_degree": G_all.degree(n, weight="weight"),
                  "betweenness": bet_all.get(n, 0.0)}
    bi = {i: nx.betweenness_centrality(G_inst[i], normalized=True) for i in INSTS}
    for f in core.itertuples():
        out[f.faculty_id]["betweenness_internal"] = bi[f.institution].get(f.faculty_id, 0.0)
    comms = {}
    for i in INSTS:
        lab = g.louvain(G_inst[i])
        comms.update({n: f"{i}-C{c}" for n, c in lab.items()})
    for n in out:
        out[n]["community"] = comms.get(n)
    cross = an[an.cross_institution.astype(str).eq("True")]
    hubs = Counter(list(cross.faculty_id_a) + list(cross.faculty_id_b))
    return out, comms, {"cross_institution_edges": int(len(cross)), "cross_institution_pairs": int(cross[["faculty_id_a", "faculty_id_b"]].drop_duplicates().shape[0]),
                        "hub_bridgers": [{"faculty_id": k, "cross_institution_papers": v} for k, v in hubs.most_common(10)]}


# ---------------------------------------------------------------------------- central question
def central_question(core, G_inst):
    res = {}
    for i in INSTS:
        G = G_inst[i]
        unit = {f.faculty_id: f.unit for f in core[core.institution == i].itertuples()}
        com = g.louvain(G)
        # unit-based comparisons use only faculty with a known unit (mostly older former
        # faculty lack one); 'Unassigned' must not act as a unit
        known = [n for n in G if unit.get(n) != "Unassigned"]
        G = G.subgraph(known).copy()
        com = {n: c for n, c in com.items() if n in G}
        active = [n for n in G if G.degree(n) > 0]
        Ga = G.subgraph(active)
        nm = g.null_model_stats(Ga, unit, samples=max(100, TH["null_model_samples"]))
        units = sorted(set(unit[n] for n in active))
        comms = sorted(set(com[n] for n in active))
        matrix = [[sum(1 for n in active if unit[n] == u and com[n] == c) for c in comms] for u in units]
        res[i] = {
            "n_faculty": G.number_of_nodes(), "n_active": len(active), "n_edges": Ga.number_of_edges(),
            "n_excluded_no_unit": int(sum(1 for n in G_inst[i] if unit.get(n) == "Unassigned")),
            "n_units": len(set(unit.values()) - {"Unassigned"}), "n_communities": len(comms),
            "nmi_units_vs_communities": g.nmi(unit, com, active),
            "modularity_communities": g.modularity_of(Ga, com), "modularity_units": g.modularity_of(Ga, unit),
            "avg_clustering": nx.average_clustering(Ga), "cross_unit_share_links": g.cross_unit_share(Ga, unit),
            "cross_unit_share_weighted": g.cross_unit_share(Ga, unit, "weight"),
            "null_model": nm, "unit_labels": units, "community_labels": [f"C{c}" for c in comms], "matrix": matrix,
            "unit_sizes": Counter(unit.values()),
        }
    return res


# ---------------------------------------------------------------------------- findings
def finding1(core, G_inst):
    rows, thr = [], {}
    name = core.set_index("faculty_id").name.to_dict()
    scatter = []
    for i in INSTS:
        G = G_inst[i]
        flagged, t = g.hidden_glue(G, TH["hidden_glue_betweenness_pct"])
        thr[i] = t
        bet = nx.betweenness_centrality(G, normalized=True)
        fl = {f["node"] for f in flagged}
        for n in G:
            scatter.append({"faculty_id": n, "name": name[n], "institution": i, "unit": G.nodes[n]["unit"],
                            "degree": G.degree(n), "betweenness": bet[n], "flagged": n in fl})
        for f in flagged:
            rows.append({"institution": i, "faculty_id": f["node"], "name": name[f["node"]], "unit": G.nodes[f["node"]]["unit"], **f})
    df = pd.DataFrame(rows, columns=["institution", "faculty_id", "name", "unit", "node", "betweenness", "degree", "lcc_before", "lcc_after", "lcc_drop", "lcc_drop_pct"])
    df.to_csv(OUT / "finding1_hidden_glue.csv", index=False)
    head = df.sort_values(["lcc_drop", "betweenness"], ascending=False).head(1).to_dict("records")
    return {"table": rows, "scatter": scatter, "thresholds": thr, "headline_person": head[0] if head else None,
            "n_flagged": {i: int((df.institution == i).sum()) if len(df) else 0 for i in INSTS}}


def finding2(core, G_inst):
    rows, per_unit = [], []
    name = core.set_index("faculty_id").name.to_dict()
    for i in INSTS:
        G = G_inst[i]
        for u, grp in core[(core.institution == i) & core.unit.ne("Unassigned")].groupby("unit"):
            H = G.subgraph(grp.faculty_id).copy()
            aps = g.articulation_report(H)
            comps = nx.number_connected_components(H)
            per_unit.append({"institution": i, "unit": u, "n_faculty": H.number_of_nodes(), "n_edges": H.number_of_edges(),
                             "isolated": sum(1 for n in H if H.degree(n) == 0), "components": comps,
                             "largest_component": g.lcc_size(H), "articulation_points": len(aps)})
            for a in aps:
                rows.append({"institution": i, "unit": u, "faculty_id": a["node"], "name": name[a["node"]], **{k: v for k, v in a.items() if k != "node"}})
    pd.DataFrame(per_unit).to_csv(OUT / "finding2_units.csv", index=False)
    pd.DataFrame(rows).to_csv(OUT / "finding2_articulation_points.csv", index=False)
    return {"per_unit": per_unit, "points": rows}


def finding3(core, ml, mp, an):
    """Internal degree (distinct same-institute faculty co-authors, cumulative) in years 1–3
    after joining, for faculty who joined 2016 or later. Year 1 = joining year."""
    yr = mp.set_index("paper_id").year.astype(int).to_dict()
    an = an.copy()
    an["y"] = an.year.astype(int)
    rows = []
    for f in core.itertuples():
        jy = pd.to_numeric(f.joining_year, errors="coerce")
        if pd.isna(jy) or jy < Y0:
            continue
        jy = int(jy)
        e = an[((an.faculty_id_a == f.faculty_id) | (an.faculty_id_b == f.faculty_id)) & ~an.cross_institution.astype(str).eq("True")]
        r = {"faculty_id": f.faculty_id, "name": f.name, "institution": f.institution, "unit": f.unit, "joining_year": jy,
             "joining_year_source": f.joining_year_source}
        for k in (1, 2, 3):
            end = jy + k - 1
            if end > Y1 - 1:  # incomplete observation window (2026 partial)
                r[f"deg_y{k}"] = None
                continue
            ee = e[e.y <= end]
            r[f"deg_y{k}"] = len(set(ee.faculty_id_a) | set(ee.faculty_id_b) - {f.faculty_id}) if len(ee) else 0
        rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "finding3_new_joiners.csv", index=False)
    summ = []
    if len(df):
        obs = df[df.deg_y3.notna()]
        for keys, grp in list(obs.groupby("institution")) + list(obs.groupby(["institution", "unit"])):
            keys = keys if isinstance(keys, tuple) else (keys, "All units")
            summ.append({"institution": keys[0], "unit": keys[1], "n": len(grp),
                         "share_zero_after_3y": float((grp.deg_y3 == 0).mean()),
                         "median_deg_y1": float(grp.deg_y1.median()), "median_deg_y2": float(grp.deg_y2.median()),
                         "median_deg_y3": float(grp.deg_y3.median())})
    return {"people": rows, "summary": summ}


def faculty_topics(ml, mp):
    tp = ml.merge(mp[["paper_id", "topic_id"]], on="paper_id")
    tp = tp[tp.topic_id.fillna("").ne("")]
    # topics appearing in ≥2 of the person's papers (or all topics if they have <5 papers)
    out = {}
    for f, grp in tp.groupby("faculty_id"):
        c = Counter(grp.topic_id)
        s = {t for t, n in c.items() if n >= 2} if len(grp) >= 5 else set(c)
        out[f] = s
    return out


def coauthor_sets(mp, ml):
    """All OpenAlex co-author IDs per faculty member (for 'no shared co-author')."""
    ids = pd.read_csv(PROCESSED / "faculty_author_ids.csv", dtype=str)
    own = ids.groupby("faculty_id").author_id.apply(set).to_dict()
    want = set(mp.openalex_id.dropna())
    pap_fac = ml.groupby("paper_id").faculty_id.apply(set).to_dict()
    pid_of = mp.set_index("openalex_id").paper_id.to_dict()
    co = defaultdict(set)
    with gzip.open(PROCESSED / "works_openalex.jsonl.gz", "rt") as fh:
        for line in fh:
            w = json.loads(line)
            wid = short_id(w["id"])
            if wid not in want:
                continue
            aus = {short_id(a["author"].get("id")) for a in w.get("authorships", [])}
            if len(aus) > cfg()["flags"]["big_paper_authors"]:
                continue  # consortium papers would make everyone share a co-author
            for f in pap_fac.get(pid_of.get(wid), ()):
                co[f] |= aus - own.get(f, set())
    return co


def finding4(core, ml, mp, G_all):
    topics = faculty_topics(ml, mp)
    co = coauthor_sets(mp, ml)
    info = core.set_index("faculty_id")
    rows = []
    # a topic set of one or two topics makes Jaccard trivially 1.0: require ≥ 3 topics each
    ids = [f for f in core.faculty_id if len(topics.get(f, ())) >= 3]
    # 'high similarity' = top 1% of topic Jaccard among all pairs of these faculty (topics are
    # fine-grained, so absolute values run low), with ≥ 3 topics in common
    all_j = [g.jaccard(topics[a], topics[b]) for a, b in itertools.combinations(ids, 2)]
    thr = float(np.quantile(all_j, 0.99)) if all_j else 1.0
    for a, b in itertools.combinations(ids, 2):
        j = g.jaccard(topics[a], topics[b])
        if j < thr or len(topics[a] & topics[b]) < 3:
            continue
        if G_all.has_edge(a, b):
            continue  # they already write together
        shared_co = len(co[a] & co[b])
        ia, ib = info.at[a, "institution"], info.at[b, "institution"]
        rows.append({"faculty_a": info.at[a, "name"], "faculty_b": info.at[b, "name"], "institution_a": ia, "institution_b": ib,
                     "unit_a": info.at[a, "unit"], "unit_b": info.at[b, "unit"], "topic_jaccard": round(j, 3),
                     "shared_topics": len(topics[a] & topics[b]), "scope": "cross-institute" if ia != ib else f"within {ia}",
                     "same_unit": ia == ib and info.at[a, "unit"] == info.at[b, "unit"], "faculty_id_a": a, "faculty_id_b": b,
                     "shared_coauthors": shared_co,
                     "tier": "1 · strangers (no joint paper, no shared co-author)" if shared_co == 0 else "2 · one introduction away (shared co-author)"})
    df = pd.DataFrame(rows).sort_values(["tier", "topic_jaccard", "shared_topics"], ascending=[True, False, False]) if rows else pd.DataFrame()
    # topic names for display
    tn = mp.drop_duplicates("topic_id").set_index("topic_id").topic.to_dict()
    if len(df):
        df["shared_topic_names"] = [", ".join(sorted(tn.get(t, t) for t in topics[a] & topics[b])[:5]) for a, b in zip(df.faculty_id_a, df.faculty_id_b)]
    df.to_csv(OUT / "finding4_missed_collaborations.csv", index=False)
    return {"pairs": df.to_dict("records"), "threshold": round(thr, 3), "threshold_rule": "top 1% of all faculty pairs, ≥ 3 shared topics", "min_topics": 3,
            "counts": df.scope.value_counts().to_dict() if len(df) else {}, "n_faculty_with_topics": len(ids),
            "tier_counts": df.tier.value_counts().to_dict() if len(df) else {}}


def finding5(core, ml, mp):
    unit = core.set_index("faculty_id").unit.to_dict()
    inst = core.set_index("faculty_id").institution.to_dict()
    lab = []
    for pid, grp in ml.groupby("paper_id"):
        if any(unit.get(f) == "Unassigned" for f in grp.faculty_id):
            continue  # a co-author's unit is unknown: cannot tell within- from cross-unit
        by_inst = defaultdict(set)
        for f in grp.faculty_id:
            by_inst[inst[f]].add(unit[f])
        multi = [u for u in by_inst.values()]
        n_fac = grp.faculty_id.nunique()
        if n_fac < 2:
            lab.append((pid, "single faculty"))
        elif any(len(u) > 1 for u in multi) or len(by_inst) > 1:
            lab.append((pid, "cross-unit"))
        else:
            lab.append((pid, "within-unit"))
    L = pd.DataFrame(lab, columns=["paper_id", "collab"]).merge(mp[["paper_id", "year", "citations", "type"]], on="paper_id")
    L["year"] = L.year.astype(int)
    L["citations"] = L.citations.fillna(0)
    med = L.groupby("year").citations.median().replace(0, np.nan)
    L["norm_cit"] = L.citations / L.year.map(med)
    by_year = L[L.collab != "single faculty"].groupby(["year", "collab"]).citations.agg(["median", "size"]).unstack("collab")
    yrs = []
    for y, r in by_year.iterrows():
        yrs.append({"year": int(y), "cross_median": r.get(("median", "cross-unit")), "within_median": r.get(("median", "within-unit")),
                    "cross_n": r.get(("size", "cross-unit")), "within_n": r.get(("size", "within-unit")), "partial": y == YP})
    full = L[L.year < YP]
    pooled = {c: {"median_norm_citations": float(grp.norm_cit.median()), "n": len(grp)} for c, grp in full.groupby("collab")}
    years_cross_wins = sum(1 for r in yrs if not r["partial"] and r["cross_median"] is not None and r["within_median"] is not None
                           and not pd.isna(r["cross_median"]) and not pd.isna(r["within_median"]) and r["cross_median"] > r["within_median"])
    years_compared = sum(1 for r in yrs if not r["partial"] and not pd.isna(r.get("cross_median")) and not pd.isna(r.get("within_median")))
    L.to_csv(OUT / "finding5_paper_labels.csv", index=False)
    return {"by_year": yrs, "pooled_year_normalised": pooled, "years_cross_higher": years_cross_wins, "years_compared": years_compared}


def in_post(r, y: int) -> bool:
    jy = pd.to_numeric(r.get("joining_year"), errors="coerce")
    jb = pd.to_numeric(r.get("joined_by_year"), errors="coerce")
    start = jy if pd.notna(jy) else (jb if pd.notna(jb) else -1)
    ly = pd.to_numeric(r.get("leaving_year"), errors="coerce")
    end = ly if (r.get("status") == "former" and pd.notna(ly)) else 9999
    return start <= y <= end


def finding6(core, ml, mp, G_inst):
    cit = mp.set_index("paper_id").citations.fillna(0).to_dict()
    yr = mp.set_index("paper_id").year.astype(int).to_dict()
    rows = []
    for i in INSTS:
        fac = core[core.institution == i].faculty_id.tolist()
        lk = ml[ml.faculty_id.isin(fac)].copy()
        lk["year"] = lk.paper_id.map(yr)
        lk["cit"] = lk.paper_id.map(cit)
        info = core.set_index("faculty_id")
        for y in list(range(Y0, Y1 + 1)) + ["all"]:
            sub = lk if y == "all" else lk[lk.year == y]
            # population = core faculty in post that year (joined by then, not yet left)
            active = fac if y == "all" else [f for f in fac if in_post(info.loc[f], y)]
            papers = sub.groupby("faculty_id").paper_id.nunique().reindex(active, fill_value=0)
            cits = sub.groupby("faculty_id").cit.sum().reindex(active, fill_value=0)
            row = {"institution": i, "year": y, "n_faculty": len(active),
                   "top10_share_papers": g.top_share(papers), "top10_share_citations": g.top_share(cits),
                   "gini_papers": g.gini(papers), "gini_citations": g.gini(cits), "partial": y == YP}
            if y == "all":
                deg = pd.Series(dict(G_inst[i].degree())).reindex(active, fill_value=0)
                row.update({"top10_share_links": g.top_share(deg), "gini_links": g.gini(deg)})
            rows.append(row)
    pd.DataFrame(rows).to_csv(OUT / "finding6_concentration.csv", index=False)
    return {"rows": rows}


def finding7(ic, edges, mp, insts):
    out = {}
    for i in INSTS:
        sub = ic[ic.your_inst == i].copy()
        if sub.empty:
            out[i] = {"partners": [], "domestic_share": None}
            continue
        sub["cit_rank_pct"] = sub.total_citations.rank(pct=True)
        sub["collab_rank_pct"] = sub.shared_papers.rank(pct=True)
        hi_cit = sub.total_citations >= sub.total_citations.quantile(0.9)
        sub["cites_us_not_collab"] = hi_cit & (sub.shared_papers <= 1)
        # domestic share: distinct (cited paper, citing work) pairs with an Indian non-own institution
        own = set(insts[i]["openalex_ids_all"])
        ours = set(mp[mp.our_institutions.str.contains(i)].openalex_id.dropna())
        e = edges[edges.cited_paper.isin(ours)]
        e = e[~e.apply(lambda r: bool(({r.partner_id} | set(str(r.partner_lineage).split(";"))) & own), axis=1)]
        dom = e[["cited_paper", "citing_work"]].drop_duplicates().shape[0]
        total = mp[mp.openalex_id.isin(ours)].citations_openalex.fillna(0).sum()
        out[i] = {"partners": sub.sort_values("total_citations", ascending=False).head(60).to_dict("records"),
                  "flagged": sub[sub.cites_us_not_collab].sort_values("total_citations", ascending=False).to_dict("records"),
                  "domestic_citing_pairs": int(dom), "total_citations": float(total),
                  "domestic_share": dom / total if total else None,
                  "citation_threshold_top10pct": float(sub.total_citations.quantile(0.9))}
        sub.to_csv(OUT / f"finding7_partners_{i}.csv", index=False)
    return out


# ---------------------------------------------------------------------------- main
def main() -> None:
    roster, core, allp, links, mp, ml, an, ic, fy, edges, cn, insts = load()
    ml = ml[ml.faculty_id.isin(core.faculty_id)]
    R = required_metrics(core, mp, ml, cn, roster)
    G_all, G_inst = coauthor_graphs(core, an)
    cm, comms, cross = collaboration_metrics(core, G_all, G_inst, an)
    for p in R["faculty"]:
        p.update(cm.get(p["faculty_id"], {}))
    CQ = central_question(core, G_inst)
    F = {"f1": finding1(core, G_inst), "f2": finding2(core, G_inst), "f3": finding3(core, ml, mp, an),
         "f4": finding4(core, ml, mp, G_all), "f5": finding5(core, ml, mp), "f6": finding6(core, ml, mp, G_inst),
         "f7": finding7(ic, edges, mp, insts)}

    # site data
    papers_site = mp.assign(faculty=mp.paper_id.map(ml.groupby("paper_id").faculty_id.apply(list)))[
        ["paper_id", "title", "year", "type", "journal_name", "acronym", "doi", "citations", "quartile", "core_rank", "field",
         "subfield", "our_institutions", "faculty", "cites_indian_inst", "cited_by_indian_inst"]]
    pre = unpublished_preprints(allp, mp, links)
    pre_site = pre.assign(faculty=pre.paper_id.map(links[links.in_main_set].groupby("paper_id").faculty_id.apply(list)),
                          our_institutions=pre.our_institutions)[["paper_id", "title", "year", "type", "doi", "citations", "field", "our_institutions", "faculty"]]
    dump("papers", papers_site.to_dict("records"))
    dump("preprints", pre_site.to_dict("records"))
    dump("faculty", R.pop("faculty"))
    dump("coauthor_graph", {"nodes": [{"id": n, **d, "community": comms.get(n), "degree": G_all.degree(n)} for n, d in G_all.nodes(data=True)],
                            "edges": [{"source": a, "target": b, "weight": d["weight"], "papers": d["papers"]} for a, b, d in G_all.edges(data=True)],
                            "edge_years": an.groupby(["faculty_id_a", "faculty_id_b"]).year.apply(lambda s: sorted(set(int(x) for x in s))).reset_index().values.tolist()})
    dump("citation_graph", R.pop("citation_graph"))
    dump("required", R)
    dump("collaboration", cross)
    dump("central", CQ)
    dump("findings", F)
    dump("indian", {"connections": ic.to_dict("records"), "flow_by_year": fy.to_dict("records"),
                    "top_citing": {i: ic[ic.your_inst == i].sort_values("total_citations", ascending=False).head(10).to_dict("records") for i in INSTS},
                    "by_partner_type": ic.groupby(["your_inst", "partner_type"]).agg(partners=("partner_inst", "size"), shared_papers=("shared_papers", "sum"),
                                                                                    citations_in=("total_citations", "sum"), citations_out=("citations_given_to_partner", "sum")).reset_index().to_dict("records")})
    from analysis.deliverables import DICTIONARY
    qa_rows = pd.read_csv(PROCESSED / "qa_summary.csv").to_dict("records") if (PROCESSED / "qa_summary.csv").exists() else []
    merge = json.loads((PROCESSED / "merge_report.json").read_text())
    dump("meta", {
        "collection_date": collection_date(), "year_start": Y0, "year_end": Y1, "partial_year": YP,
        "quartile_source": QUARTILE_SOURCE,
        "qa_rows": qa_rows + [{"metric": "fuzzy_title_threshold", "value": merge["fuzzy_threshold_used"]},
                              {"metric": "overmerge_filtered_links", "value": merge["overmerge_filtered"]}],
        "sources": [
            "OpenAlex (primary): works, authors, institutions, topics, citations, references — https://openalex.org",
            "DBLP: per-person publication lists, journal/conference record type — https://dblp.org",
            "Crossref: DOIs, ISSNs, container titles, types — https://www.crossref.org",
            "Semantic Scholar (keyless, best-effort): secondary citation counts — https://www.semanticscholar.org",
            "IIIT-H publications portal (institute-reported records, CORE labels) — https://iiit.ac.in/publications/",
            "Official faculty pages of IIIT-H and IIIT-D, personal homepages and CVs; Wayback Machine snapshots for former faculty",
            "ROR for institution identifiers — https://ror.org",
            "Scimago Journal Rank (SJR) quartiles 2016–2025 — https://www.scimagojr.com",
            "CORE conference rankings — https://portal.core.edu.au/conf-ranks/",
        ],
        "choices": [
            "Faculty: core faculty only (Assistant/Associate/Full Professor); adjunct, visiting, emeritus, distinguished, affiliate and Professors of Practice are kept in the data but excluded from the analysis.",
            "Paper set: journal and conference papers 2016–2026 where the faculty member lists IIIT-H/IIIT-D on the paper or the paper falls on/after their joining year; earlier unaffiliated papers go to the pre-joining sheet.",
            f"Preprints: arXiv versions are merged into the published paper; arXiv-only works are excluded by default (toggle 'incl. preprints').",
            f"Deduplication: DOI first, then normalised title (fuzzy ratio ≥ {merge['fuzzy_threshold_used']}) + year ±1 (±2 for preprints) + a shared faculty member.",
            "Co-authorship networks: faculty-only nodes; edge weight Σ 1/(n_authors − 1); papers with > 25 authors flagged (their weight is already ≤ 1/25).",
            "Degree, betweenness, articulation points: unweighted graphs. Communities: Louvain (seed 42) on the weighted within-institute graph.",
            f"Null model: {max(100, TH['null_model_samples'])} degree-preserving rewirings (double-edge swaps) per institute.",
            "h-index (dataset): from OpenAlex citations of main-set papers 2016–2026. h-index (lifetime): OpenAlex summary_stats, max over the person's author IDs.",
            "Quartile: Scimago best quartile across categories, for the paper's year (nearest available year otherwise). CORE: edition in force at publication.",
            "Indian citation flags exclude the paper's own institute(s); counts are per (citation × partner institution).",
            f"{YP} is a partial year everywhere; year-over-year comparisons use full years only.",
            "Small groups: every unit- or group-level number is shown with its group size.",
        ],
        "dictionary": [[c, d] for c, s, d in DICTIONARY if s == "group9_data"],
        "panels": [
            ["1. Publication trend 2016–2026", "Overview, Publications"], ["2. Q1 fraction (with CORE A*/A share)", "Venues & Quality, Overview"],
            ["3. Faculty h-index distribution", "Faculty"], ["4. Faculty list / performance table", "Faculty"],
            ["5. Top journals and conferences", "Publications, Venues & Quality"], ["6. Top 10 most-cited papers", "Publications"],
            ["7. Research area breakdown", "Research Areas"], ["8. Citation network (in-degree, PageRank, flow)", "Citation Network"],
            ["9. Authorship network (degree, betweenness, communities)", "Collaboration Network, Centres vs Departments"],
            ["10. Citation flow with Indian institutes", "Indian Connections"], ["11. Connectivity map of Indian partners", "Indian Connections, Findings (7)"],
        ],
    })
    json.dump(clean({"central": CQ, "findings_headlines": {k: {kk: vv for kk, vv in v.items() if kk in ("thresholds", "n_flagged", "counts", "pooled_year_normalised", "years_cross_higher", "years_compared")} for k, v in F.items()}}),
              open(OUT / "analysis_summary.json", "w"), indent=1, default=str)
    print("analysis done:", {k: (len(v) if hasattr(v, "__len__") else v) for k, v in F.items()})
    for i in INSTS:
        c = CQ[i]
        print(f"{i}: NMI {c['nmi_units_vs_communities']:.3f}, modularity {c['modularity_communities']:.3f}, cross-unit {c['cross_unit_share_links']:.2%}, z_clust {c['null_model']['z'].get('clustering')}")


if __name__ == "__main__":
    main()
