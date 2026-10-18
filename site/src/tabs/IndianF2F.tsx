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

  const findings = useMemo(() => {
    const allEdges = indianF2f.external_edges as any[];
    const allNodes = indianF2f.external_nodes as any[];
    const ourNodes: Record<string, any> = {};
    const partnerNodes: Record<string, any> = {};
    for (const n of allNodes) { if (n.is_ours) ourNodes[n.id] = n; else partnerNodes[n.id] = n; }

    const facPapers: Record<string, { name: string; inst: string; papers: number }> = {};
    for (const e of allEdges) {
      const ours = e.source in ourNodes ? e.source : e.target;
      const n = ourNodes[ours];
      if (!n) continue;
      if (!facPapers[ours]) facPapers[ours] = { name: n.name, inst: n.inst, papers: 0 };
      facPapers[ours].papers += e.papers;
    }
    const sorted = Object.values(facPapers).sort((a, b) => b.papers - a.papers);
    const total = sorted.reduce((s, x) => s + x.papers, 0);
    let running = 0, topN = 0;
    for (const x of sorted) { running += x.papers; topN++; if (running >= total * 0.5) break; }

    const instPapers: Record<string, number> = {};
    for (const n of Object.values(partnerNodes)) instPapers[n.inst] = (instPapers[n.inst] || 0) + 1;
    const topInsts = Object.entries(instPapers).sort((a, b) => b[1] - a[1]).slice(0, 5);

    const hPapers = Object.values(facPapers).filter((x) => x.inst === "IIIT-H").reduce((s, x) => s + x.papers, 0);
    const dPapers = Object.values(facPapers).filter((x) => x.inst === "IIIT-D").reduce((s, x) => s + x.papers, 0);
    const hFac = Object.values(facPapers).filter((x) => x.inst === "IIIT-H").length;
    const dFac = Object.values(facPapers).filter((x) => x.inst === "IIIT-D").length;

    const crossInt = (indianF2f.internal_edges as any[]).filter((e: any) => e.cross_inst);

    return { sorted, topN, totalFac: sorted.length, topInsts, hPapers, dPapers, hFac, dFac, crossInt, top5: sorted.slice(0, 5) };
  }, []);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Kpi label="External Indian collaborators" value={fmt(summary.unique_indian_partners)} sub="unique individuals at Indian institutions" />
        <Kpi label="External collaboration edges" value={fmt(summary.total_external_edges)} sub="faculty × Indian partner pairs" />
        <Kpi label="Internal edges (Indian papers)" value={fmt(summary.total_internal_edges)} sub="faculty pairs co-authoring Indian-connected papers" />
        <Kpi label="Cross-institute (Indian papers)" value={fmt(summary.internal_cross_inst)} sub="IIIT-H ↔ IIIT-D edges on Indian-connected papers" />
      </div>

      <section className="card p-5">
        <h3 className="font-semibold text-[15px] mb-3">Key findings</h3>
        <ul className="flex flex-col gap-2 text-[13px]">
          <li><strong>Highly concentrated:</strong> The top {findings.topN} faculty (of {findings.totalFac} with Indian collaborators) account for 50% of all Indian collaboration papers. The most prolific are {findings.top5.map((x) => `${x.name} (${x.inst})`).join(", ")}.</li>
          <li><strong>IIIT-D collaborates more within India:</strong> {findings.dFac} IIIT-D faculty produced {fmt(findings.dPapers)} Indian co-authored papers vs. {findings.hFac} IIIT-H faculty with {fmt(findings.hPapers)} — {((findings.dPapers / Math.max(findings.dFac, 1)) / (findings.hPapers / Math.max(findings.hFac, 1))).toFixed(1)}× higher rate per faculty at IIIT-D.</li>
          <li><strong>Top Indian partners:</strong> {findings.topInsts.map(([inst, cnt]) => `${inst} (${cnt})`).join(", ")}. Geographic proximity matters — IIT Delhi and AIIMS dominate IIIT-D's partner list.</li>
          <li><strong>Narrow cross-institute bridge:</strong> Only {findings.crossInt.length} faculty pairs bridge IIIT-H and IIIT-D on Indian-connected papers{findings.crossInt.length > 0 ? `, led by ${findings.crossInt.sort((a: any, b: any) => b.papers - a.papers)[0]?.name_a} ↔ ${findings.crossInt.sort((a: any, b: any) => b.papers - a.papers)[0]?.name_b} (${findings.crossInt.sort((a: any, b: any) => b.papers - a.papers)[0]?.papers} papers)` : ""}. Indian collaboration is largely institute-internal.</li>
        </ul>
      </section>

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
