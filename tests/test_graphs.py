import networkx as nx

from analysis.graphs import (articulation_report, cross_unit_share, faculty_graph, gini, hidden_glue,
                             null_model_stats, removal_impact, top_share)


def two_cliques_with_bridge():
    G = nx.Graph()
    G.add_edges_from(nx.complete_graph(["a1", "a2", "a3", "a4"]).edges())
    G.add_edges_from(nx.complete_graph(["b1", "b2", "b3", "b4"]).edges())
    G.add_edges_from([("a1", "x"), ("x", "b1")])  # x: low degree, high betweenness
    return G


def test_faculty_graph_accumulates_weights():
    G = faculty_graph({"a": {}, "b": {}, "c": {}}, [("a", "b", 0.5, "p1"), ("b", "a", 1.0, "p2"), ("a", "z", 1, "p3")])
    assert G["a"]["b"]["weight"] == 1.5 and G["a"]["b"]["papers"] == 2
    assert G.number_of_nodes() == 3 and "c" in G  # isolate kept, unknown node ignored


def test_hidden_glue_flags_bridge():
    flagged, thr = hidden_glue(two_cliques_with_bridge(), bet_pct=0.85)
    assert [f["node"] for f in flagged] == ["x"]
    assert flagged[0]["lcc_after"] == 4 and flagged[0]["lcc_before"] == 9


def test_removal_impact_counts_node_itself():
    r = removal_impact(two_cliques_with_bridge(), "a2")
    assert r["lcc_drop"] == 0


def test_articulation_points():
    aps = {r["node"]: r for r in articulation_report(two_cliques_with_bridge())}
    assert set(aps) == {"a1", "x", "b1"}
    assert aps["x"]["cut_off"] == 4


def test_cross_unit_share():
    G = two_cliques_with_bridge()
    unit = {n: n[0] for n in G}
    assert abs(cross_unit_share(G, unit) - 2 / 14) < 1e-9


def test_null_model_shapes():
    G = two_cliques_with_bridge()
    unit = {n: n[0] for n in G}
    s = null_model_stats(G, unit, samples=10)
    assert s["samples"] == 10 and s["observed"]["clustering"] > s["null_mean"]["clustering"]


def test_concentration_measures():
    assert abs(gini([1, 1, 1, 1])) < 1e-9
    assert top_share([100] + [0] * 9, 0.1) == 1.0
