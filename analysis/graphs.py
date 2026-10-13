"""Network primitives used by the analysis: faculty co-authorship graphs, community/unit
comparison, degree-preserving null models, bridge/articulation diagnostics."""
from __future__ import annotations

import random
from collections import Counter

import networkx as nx
import numpy as np
from sklearn.metrics import normalized_mutual_info_score

SEED = 42


def faculty_graph(nodes: dict[str, dict], edges) -> nx.Graph:
    """nodes: {faculty_id: attrs}; edges: iterable of (a, b, weight, paper_id).
    Edge attrs: weight = Σ 1/(n_authors-1) over shared papers, papers = #shared papers."""
    G = nx.Graph()
    for n, a in nodes.items():
        G.add_node(n, **a)
    for a, b, w, pid in edges:
        if a not in G or b not in G or a == b:
            continue
        if G.has_edge(a, b):
            G[a][b]["weight"] += w
            G[a][b]["papers"] += 1
        else:
            G.add_edge(a, b, weight=w, papers=1)
    return G


def louvain(G: nx.Graph, weight: str | None = "weight", seed: int = SEED) -> dict[str, int]:
    if G.number_of_edges() == 0:
        return {n: i for i, n in enumerate(G)}
    comms = nx.community.louvain_communities(G, weight=weight, seed=seed)
    comms = sorted(comms, key=len, reverse=True)
    return {n: i for i, c in enumerate(comms) for n in c}


def modularity_of(G: nx.Graph, labels: dict[str, object], weight: str | None = "weight") -> float:
    if G.number_of_edges() == 0:
        return float("nan")
    groups: dict[object, set] = {}
    for n in G:
        groups.setdefault(labels.get(n), set()).add(n)
    return nx.community.modularity(G, groups.values(), weight=weight)


def cross_unit_share(G: nx.Graph, unit: dict[str, str], weight: str | None = None) -> float:
    """Share of collaboration links (or weight) joining two different units."""
    tot = cross = 0.0
    for a, b, d in G.edges(data=True):
        w = d.get(weight, 1.0) if weight else 1.0
        tot += w
        if unit.get(a) != unit.get(b):
            cross += w
    return cross / tot if tot else float("nan")


def nmi(labels_a: dict[str, object], labels_b: dict[str, object], nodes) -> float:
    nodes = [n for n in nodes if n in labels_a and n in labels_b]
    if len(nodes) < 3:
        return float("nan")
    return float(normalized_mutual_info_score([str(labels_a[n]) for n in nodes], [str(labels_b[n]) for n in nodes]))


def null_model_stats(G: nx.Graph, unit: dict[str, str], samples: int = 200, seed: int = SEED) -> dict:
    """Degree-preserving randomisation (double-edge swaps on the simple graph, 10×|E| swaps per
    sample). Returns observed values, null mean/sd, z-scores and observed/null ratios for:
    average clustering, Louvain modularity, cross-unit share."""
    H = nx.Graph(G.edges())  # unweighted simple topology
    H.add_nodes_from(G)
    obs = {"clustering": nx.average_clustering(H), "modularity": modularity_of(H, louvain(H, None), None),
           "cross_unit_share": cross_unit_share(H, unit)}
    rng = random.Random(seed)
    vals = {k: [] for k in obs}
    m = H.number_of_edges()
    if m < 4:
        return {"observed": obs, "null_mean": {}, "null_sd": {}, "z": {}, "ratio": {}, "samples": 0}
    for _ in range(samples):
        R = H.copy()
        try:
            nx.double_edge_swap(R, nswap=10 * m, max_tries=100 * m, seed=rng.randrange(1 << 30))
        except nx.NetworkXAlgorithmError:
            pass  # very dense/small graphs: keep the partially swapped graph
        vals["clustering"].append(nx.average_clustering(R))
        vals["modularity"].append(modularity_of(R, louvain(R, None, seed=rng.randrange(1 << 30)), None))
        vals["cross_unit_share"].append(cross_unit_share(R, unit))
    mean = {k: float(np.mean(v)) for k, v in vals.items()}
    sd = {k: float(np.std(v, ddof=1)) for k, v in vals.items()}
    z = {k: (obs[k] - mean[k]) / sd[k] if sd[k] > 0 else float("nan") for k in obs}
    ratio = {k: obs[k] / mean[k] if mean[k] else float("nan") for k in obs}
    return {"observed": obs, "null_mean": mean, "null_sd": sd, "z": z, "ratio": ratio, "samples": samples}


def lcc_size(G: nx.Graph) -> int:
    return max((len(c) for c in nx.connected_components(G)), default=0)


def removal_impact(G: nx.Graph, node) -> dict:
    """LCC size before/after removing `node` (the node itself excluded from 'after')."""
    before = lcc_size(G)
    H = G.copy()
    H.remove_node(node)
    after = lcc_size(H)
    return {"lcc_before": before, "lcc_after": after, "lcc_drop": before - 1 - after if before else 0,
            "lcc_drop_pct": (before - 1 - after) / before if before else 0.0}


def hidden_glue(G: nx.Graph, bet_pct: float = 0.85, deg_pct: float = 0.75) -> tuple[list[dict], dict]:
    """Nodes with betweenness in the top (1 − bet_pct) whose degree is ordinary, i.e. not in
    the top quarter (≤ the deg_pct quantile). Also reports how many pass the stricter
    'degree below the median' rule."""
    bet = nx.betweenness_centrality(G, normalized=True)
    deg = dict(G.degree())
    connected = [n for n in G if deg[n] > 0]
    if not connected:
        return [], {}
    b_thr = float(np.quantile([bet[n] for n in connected], bet_pct))
    d_med = float(np.median([deg[n] for n in connected]))
    d_thr = float(np.quantile([deg[n] for n in connected], deg_pct))
    flagged, strict = [], 0
    for n in connected:
        if bet[n] >= b_thr and bet[n] > 0 and deg[n] <= d_thr:
            flagged.append({"node": n, "betweenness": bet[n], "degree": deg[n], **removal_impact(G, n)})
            strict += deg[n] < d_med
    flagged.sort(key=lambda r: -r["betweenness"])
    return flagged, {"betweenness_threshold": b_thr, "betweenness_percentile": bet_pct, "degree_median": d_med,
                     "degree_threshold": d_thr, "degree_percentile": deg_pct, "n_flagged_strict_median_rule": strict,
                     "n_connected": len(connected)}


def articulation_report(G: nx.Graph) -> list[dict]:
    """Articulation points with how many nodes each would cut off from its component."""
    out = []
    for ap in nx.articulation_points(G):
        comp = nx.node_connected_component(G, ap)
        H = G.subgraph(comp - {ap})
        parts = sorted((len(c) for c in nx.connected_components(H)), reverse=True)
        out.append({"node": ap, "component_size": len(comp), "cut_off": sum(parts[1:]), "pieces": len(parts)})
    return sorted(out, key=lambda r: -r["cut_off"])


def gini(x) -> float:
    x = np.sort(np.asarray([v for v in x if v is not None], dtype=float))
    if len(x) == 0 or x.sum() == 0:
        return float("nan")
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def top_share(x, frac: float = 0.10) -> float:
    x = np.sort(np.asarray(list(x), dtype=float))[::-1]
    if len(x) == 0 or x.sum() == 0:
        return float("nan")
    k = max(1, int(np.ceil(frac * len(x))))
    return float(x[:k].sum() / x.sum())


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0
