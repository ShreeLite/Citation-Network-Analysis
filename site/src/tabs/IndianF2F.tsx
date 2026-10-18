/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { indianF2f, INSTS, facultyById } from "../data";
import { useFilters } from "../filters";
import { cssVar, DataTable, fmt, instColor, Kpi, Section } from "../components/ui";
import { Network, type NetEdge, type NetNode } from "../components/Network";

const ch = createColumnHelper<any>();

const MIN_PAPERS_OPTIONS = [1, 2, 3, 5] as const;

export default function IndianF2F() {
  const { f, facIds } = useFilters();
  const insts = f.inst === "both" ? INSTS : [f.inst];
  const [view, setView] = useState<"external" | "internal">("external");
  const [minPapers, setMinPapers] = useState(2);

  // External: our faculty <-> Indian partners
  const ext = useMemo(() => {
    const nodes = (indianF2f.external_nodes as any[]).filter((n: any) => {
      if (n.is_ours) return insts.some((i) => n.inst === i) && facIds.has(n.id);
      return true;
    });
    const nodeIds = new Set(nodes.map((n: any) => n.id));
    const edges = (indianF2f.external_edges as any[]).filter((e: any) => nodeIds.has(e.source) && nodeIds.has(e.target)
      && e.papers >= minPapers
      && (!e.years?.length || e.years.some((y: number) => y >= f.y0 && y <= f.y1)));
    const connectedTargets = new Set(edges.map((e: any) => e.target));
    const connectedSources = new Set(edges.map((e: any) => e.source));
    const connectedNodes = nodes.filter((n: any) => connectedSources.has(n.id) || connectedTargets.has(n.id));
    return { nodes: connectedNodes, edges };
  }, [facIds, insts.join(), f.y0, f.y1, minPapers]); // eslint-disable-line react-hooks/exhaustive-deps

  // Internal: our faculty <-> our faculty on Indian-connected papers
  const int = useMemo(() => {
    const edges = (indianF2f.internal_edges as any[]).filter((e: any) =>
      facIds.has(e.faculty_id_a) && facIds.has(e.faculty_id_b)
      && e.papers >= minPapers
      && insts.some((i) => e.inst_a === i || e.inst_b === i)
      && (!e.years?.length || e.years.some((y: number) => y >= f.y0 && y <= f.y1)));
    const nodeIds = new Set(edges.flatMap((e: any) => [e.faculty_id_a, e.faculty_id_b]));
    const nodes = [...nodeIds].map((id) => {
      const fac = facultyById[id];
      return fac ? { id, name: fac.name, inst: fac.institution } : { id, name: id, inst: "" };
    });
    return { nodes, edges };
  }, [facIds, insts.join(), f.y0, f.y1, minPapers]); // eslint-disable-line react-hooks/exhaustive-deps

  const extNetNodes: NetNode[] = useMemo(() => ext.nodes.map((n: any) => ({
    id: n.id, label: n.name, group: n.is_ours ? n.inst : "Indian partner", size: Math.max(1, n.papers), inst: n.inst,
  })), [ext.nodes]);
  const extNetEdges: NetEdge[] = useMemo(() => ext.edges.map((e: any) => ({
    source: e.source, target: e.target, weight: e.papers,
  })), [ext.edges]);

  const intNetNodes: NetNode[] = useMemo(() => int.nodes.map((n: any) => ({
    id: n.id, label: n.name, group: n.inst, size: int.edges.filter((e: any) => e.faculty_id_a === n.id || e.faculty_id_b === n.id).reduce((s: number, e: any) => s + e.papers, 0) + 1,
  })), [int.nodes, int.edges]);
  const intNetEdges: NetEdge[] = useMemo(() => int.edges.map((e: any) => ({
    source: e.faculty_id_a, target: e.faculty_id_b, weight: e.papers,
  })), [int.edges]);

  const extColor = (grp: string) => grp === "Indian partner" ? cssVar("--good") : instColor(grp);
  const intColor = (grp: string) => instColor(grp);

  const extCols = useMemo(() => [
    ch.accessor("our_name", { header: "Our faculty" }),
    ch.accessor("our_inst", { header: "Institute" }),
    ch.accessor("ext_name", { header: "Indian collaborator" }),
    ch.accessor("ext_inst", { header: "Partner institution" }),
    ch.accessor("papers", { header: "Joint papers" }),
  ], []);

  const intCols = useMemo(() => [
    ch.accessor("name_a", { header: "Faculty A" }),
    ch.accessor("inst_a", { header: "Inst. A" }),
    ch.accessor("name_b", { header: "Faculty B" }),
    ch.accessor("inst_b", { header: "Inst. B" }),
    ch.accessor("papers", { header: "Papers" }),
    ch.accessor("cross_inst", { header: "Cross-inst.", cell: (c) => c.getValue() ? "Yes" : "No" }),
  ], []);

  // Flatten external edges for table (aggregate by our_faculty + ext partner)
  const extTable = useMemo(() => {
    const m: Record<string, any> = {};
    for (const e of ext.edges) {
      const src = ext.nodes.find((n: any) => n.id === e.source);
      const tgt = ext.nodes.find((n: any) => n.id === e.target);
      if (!src || !tgt) continue;
      const our = src.is_ours ? src : tgt;
      const partner = src.is_ours ? tgt : src;
      const k = `${our.id}|${partner.id}`;
      if (!m[k]) m[k] = { our_name: our.name, our_inst: our.inst, ext_name: partner.name, ext_inst: partner.inst, papers: 0 };
      m[k].papers += e.papers;
    }
    return Object.values(m).sort((a, b) => b.papers - a.papers);
  }, [ext]);

  const summary = indianF2f.summary as any;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Kpi label="External Indian collaborators" value={fmt(summary.unique_indian_partners)} sub="unique individuals at Indian institutions" />
        <Kpi label="External collaboration edges" value={fmt(summary.total_external_edges)} sub="faculty × Indian partner pairs" />
        <Kpi label="Internal edges (Indian papers)" value={fmt(summary.total_internal_edges)} sub="faculty pairs co-authoring Indian-connected papers" />
        <Kpi label="Cross-institute (Indian papers)" value={fmt(summary.internal_cross_inst)} sub="IIIT-H ↔ IIIT-D edges on Indian-connected papers" />
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[13px] no-print">
        <span>View:</span>
        <button className={`btn ${view === "external" ? "btn-primary" : ""}`} onClick={() => setView("external")}>Our faculty ↔ Indian partners</button>
        <button className={`btn ${view === "internal" ? "btn-primary" : ""}`} onClick={() => setView("internal")}>Our faculty ↔ our faculty (Indian papers)</button>
        <span className="flex-1" />
        <label className="flex items-center gap-1.5">Min. joint papers:
          <select value={minPapers} onChange={(e) => setMinPapers(Number(e.target.value))}>
            {MIN_PAPERS_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>

      {view === "external" && (
        <>
          <Section title="Faculty ↔ Indian partner network" intro={`Each edge is a co-authored paper between one of our faculty and a researcher at an Indian institution. Green = Indian partner, blue/orange = our faculty. ${extNetNodes.length} people, ${extNetEdges.length} edges in current filter.`}>
            <div className="card p-4">
              {extNetNodes.length > 0 ? (
                <Network nodes={extNetNodes} edges={extNetEdges} colorOf={extColor} height={560}
                  legend={[{ label: "IIIT-H", color: instColor("IIIT-H") }, { label: "IIIT-D", color: instColor("IIIT-D") }, { label: "Indian partner", color: cssVar("--good") }]} />
              ) : <p className="muted text-center py-12">No connections in the current filter.</p>}
            </div>
          </Section>
          <DataTable title="Faculty ↔ Indian partner edges" data={extTable} columns={extCols} filename="indian_f2f_external.csv" pageSize={20} />
        </>
      )}

      {view === "internal" && (
        <>
          <Section title="Internal co-authorship on Indian-connected papers" intro={`Faculty pairs who co-authored papers that cite or are cited by other Indian institutions. ${intNetNodes.length} faculty, ${intNetEdges.length} edges.`}>
            <div className="card p-4">
              {intNetNodes.length > 0 ? (
                <Network nodes={intNetNodes} edges={intNetEdges} colorOf={intColor} height={560}
                  legend={[{ label: "IIIT-H", color: instColor("IIIT-H") }, { label: "IIIT-D", color: instColor("IIIT-D") }]} />
              ) : <p className="muted text-center py-12">No connections in the current filter.</p>}
            </div>
          </Section>
          <DataTable title="Internal edges on Indian-connected papers" data={int.edges} columns={intCols} filename="indian_f2f_internal.csv" pageSize={20} />
        </>
      )}
    </div>
  );
}
