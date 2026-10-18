"""Generate Indian faculty-to-faculty connection data for the site.

Two views:
1. our_faculty <-> external_indian: edges between our faculty and coauthors at Indian institutions
2. internal_on_indian_papers: our faculty co-authorship edges restricted to papers with Indian connections
"""
import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import PROCESSED, DATA, SITE_DATA

OUR_INSTS = {"IIIT-H": "International Institute of Information Technology, Hyderabad",
             "IIIT-D": "Indraprastha Institute of Information Technology Delhi"}


def main():
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    core = roster[roster.is_core.eq("True")].copy()
    our_names = {str(r["name"]).strip(): r.faculty_id for _, r in core.iterrows()}
    our_fids = set(core.faculty_id)

    an_all = pd.read_csv(PROCESSED / "authorship_network_all_coauthors.csv")
    an_fac = pd.read_csv(PROCESSED / "authorship_network.csv")

    # View 1: our faculty <-> external Indian authors
    our_long = set(OUR_INSTS.values())
    ext_edges = []
    ext_author_info = {}
    edge_counter = defaultdict(lambda: {"papers": 0, "years": set()})

    for _, row in an_all.iterrows():
        a_is_ours = row.inst_a in our_long
        b_is_ours = row.inst_b in our_long
        if a_is_ours == b_is_ours:
            continue
        our_author = row.author_a if a_is_ours else row.author_b
        our_inst_long = row.inst_a if a_is_ours else row.inst_b
        ext_author = row.author_b if a_is_ours else row.author_a
        ext_inst = row.inst_b if a_is_ours else row.inst_a

        if not isinstance(ext_inst, str):
            continue
        is_indian = False
        indian_kw = ["India", "Indian", "IIT", "NIT", "IIIT", "IISER", "IISc", "TIFR", "AIIMS",
                      "Jawaharlal Nehru", "Delhi", "Mumbai", "Chennai", "Kolkata", "Bangalore",
                      "Hyderabad", "Pune", "Bhubaneswar", "Roorkee", "Kanpur", "Kharagpur",
                      "Guwahati", "Madras", "Bombay"]
        ext_inst_lower = ext_inst.lower()
        for kw in indian_kw:
            if kw.lower() in ext_inst_lower:
                is_indian = True
                break
        if not is_indian:
            continue

        our_fid = our_names.get(our_author.strip())
        if not our_fid:
            continue

        key = (our_fid, ext_author.strip(), ext_inst)
        edge_counter[key]["papers"] += 1
        if pd.notna(row.year):
            edge_counter[key]["years"].add(int(row.year))
        ext_author_info[ext_author.strip()] = ext_inst

    external_edges = []
    for (our_fid, ext_name, ext_inst), info in edge_counter.items():
        our_row = core[core.faculty_id == our_fid].iloc[0] if our_fid in our_fids else None
        if our_row is None:
            continue
        our_inst_short = our_row.institution
        external_edges.append({
            "our_faculty_id": our_fid,
            "our_name": our_row["name"],
            "our_inst": our_inst_short,
            "ext_name": ext_name,
            "ext_inst": ext_inst,
            "papers": info["papers"],
            "years": sorted(info["years"]),
        })

    # View 2: our faculty <-> our faculty on Indian-connected papers
    mp = pd.read_parquet(PROCESSED / "main_papers.parquet")
    ml = pd.read_parquet(PROCESSED / "main_links.parquet")
    ml = ml[ml.faculty_id.isin(our_fids)]

    indian_papers = set(mp[mp.cites_indian_inst | mp.cited_by_indian_inst].paper_id)
    indian_links = ml[ml.paper_id.isin(indian_papers)]
    paper_faculty = indian_links.groupby("paper_id").faculty_id.apply(list).to_dict()

    internal_edges_counter = defaultdict(lambda: {"papers": 0, "years": set()})
    paper_years = mp.set_index("paper_id").year.to_dict()
    for pid, fids in paper_faculty.items():
        if len(fids) < 2:
            continue
        yr = paper_years.get(pid)
        for i in range(len(fids)):
            for j in range(i + 1, len(fids)):
                key = tuple(sorted([fids[i], fids[j]]))
                internal_edges_counter[key]["papers"] += 1
                if yr:
                    internal_edges_counter[key]["years"].add(int(yr))

    internal_edges = []
    for (fid_a, fid_b), info in internal_edges_counter.items():
        row_a = core[core.faculty_id == fid_a]
        row_b = core[core.faculty_id == fid_b]
        if row_a.empty or row_b.empty:
            continue
        internal_edges.append({
            "faculty_id_a": fid_a,
            "name_a": row_a.iloc[0]["name"],
            "inst_a": row_a.iloc[0]["institution"],
            "faculty_id_b": fid_b,
            "name_b": row_b.iloc[0]["name"],
            "inst_b": row_b.iloc[0]["institution"],
            "papers": info["papers"],
            "years": sorted(info["years"]),
            "cross_inst": row_a.iloc[0]["institution"] != row_b.iloc[0]["institution"],
        })

    # Aggregate external edges into nodes for the network viz
    ext_our_nodes = {}
    ext_ext_nodes = {}
    for e in external_edges:
        if e["our_faculty_id"] not in ext_our_nodes:
            ext_our_nodes[e["our_faculty_id"]] = {"id": e["our_faculty_id"], "name": e["our_name"], "inst": e["our_inst"], "is_ours": True, "papers": 0}
        ext_our_nodes[e["our_faculty_id"]]["papers"] += e["papers"]

        ext_key = f"ext:{e['ext_name']}"
        if ext_key not in ext_ext_nodes:
            ext_ext_nodes[ext_key] = {"id": ext_key, "name": e["ext_name"], "inst": e["ext_inst"], "is_ours": False, "papers": 0}
        ext_ext_nodes[ext_key]["papers"] += e["papers"]

    data = {
        "external_nodes": list(ext_our_nodes.values()) + list(ext_ext_nodes.values()),
        "external_edges": [{"source": e["our_faculty_id"], "target": f"ext:{e['ext_name']}", "papers": e["papers"], "years": e["years"]} for e in external_edges],
        "internal_edges": internal_edges,
        "summary": {
            "total_external_edges": len(external_edges),
            "unique_indian_partners": len(ext_ext_nodes),
            "total_internal_edges": len(internal_edges),
            "internal_cross_inst": sum(1 for e in internal_edges if e["cross_inst"]),
        }
    }

    out_path = SITE_DATA / "indian_f2f.json"
    with open(out_path, "w") as f:
        json.dump(data, f)
    print(f"Indian F2F data: {len(external_edges)} external edges, {len(ext_ext_nodes)} Indian partners, {len(internal_edges)} internal edges → {out_path}")


if __name__ == "__main__":
    main()
