import { useMemo, useState } from "react";
import { citationGraph, required } from "../data";
import { useFilters } from "../filters";
import { ChartCard, cssVar, fmt, instColor, Section } from "../components/ui";
import { Network, type NetEdge, type NetNode } from "../components/Network";

interface CNode { id: string; pr: number; indeg: number; inst: string; year: number; title: string; venue: string }

export default function CitationNet() {
  const { f } = useFilters();
  const [k, setK] = useState(200);
  const g = useMemo(() => {
    const all = (citationGraph.nodes as CNode[]).filter((n) => n.year >= f.y0 && n.year <= f.y1 && (f.inst === "both" || n.inst.split(";").includes(f.inst)));
    const keep = all.sort((a, b) => b.pr - a.pr).slice(0, k);
    const ids = new Set(keep.map((n) => n.id));
    const nodes: NetNode[] = keep.map((n) => ({ id: n.id, label: `${n.title.slice(0, 60)}${n.title.length > 60 ? "…" : ""} (${n.venue || "—"} ${n.year})`, group: n.inst.includes(";") ? "both" : n.inst, size: n.indeg + 1 }));
    const edges: NetEdge[] = (citationGraph.edges as [string, string][]).filter(([a, b]) => ids.has(a) && ids.has(b)).map(([a, b]) => ({ source: a, target: b }));
    return { nodes, edges };
  }, [f.y0, f.y1, f.inst, k]);
  const cn = required.citation_network;
  const dist = cn.in_degree_distribution as [number, number][];
  const color = (grp: string) => (grp === "both" ? cssVar("--ink-2") : instColor(grp));
  return (
    <div className="flex flex-col gap-5">
      <Section title="Who cites whom inside the IIIT corpus" intro={`${fmt(cn.nodes)} papers, ${fmt(cn.edges)} citations between them, ${fmt(cn.external_edges)} citations to outside work. The graph shows the top papers by PageRank among those in the current year/institute filter.`}>
        <div className="card p-4 flex flex-col gap-3">
          <label className="text-[13px] flex items-center gap-2 no-print">Papers shown (top k by PageRank):
            <input type="range" min={50} max={600} step={50} value={k} onChange={(e) => setK(Number(e.target.value))} aria-label="number of papers" />
            <span className="tabnum">{k}</span></label>
          <Network nodes={g.nodes} edges={g.edges} directed colorOf={color} height={560}
            legend={[{ label: "IIIT-H", color: instColor("IIIT-H") }, { label: "IIIT-D", color: instColor("IIIT-D") }, { label: "joint", color: cssVar("--ink-2") }]} />
          <p className="text-[12px] muted">Node size = in-degree within the corpus. Arrows point from citing to cited paper. Hover a node for its title and neighbours.</p>
        </div>
      </Section>
      <div className="grid lg:grid-cols-2 gap-4">
        <section className="card p-5 overflow-x-auto">
          <h3 className="font-semibold text-[15px] mb-2">PageRank top 10</h3>
          <table className="data tabnum"><thead><tr><th>#</th><th>Title</th><th>Venue</th><th>Year</th><th>Inst.</th><th>In-deg.</th></tr></thead>
            <tbody>{(cn.pagerank_top10 as { openalex_id: string; title: string; venue: string; year: number; institution: string; in_degree: number; doi?: string }[]).map((r, i) => (
              <tr key={r.openalex_id}><td>{i + 1}</td><td className="max-w-[320px]">{r.doi ? <a className="link" href={`https://doi.org/${r.doi}`} target="_blank" rel="noreferrer">{r.title}</a> : r.title}</td><td>{r.venue}</td><td>{r.year}</td><td>{r.institution}</td><td>{r.in_degree}</td></tr>))}</tbody></table>
        </section>
        <ChartCard title="In-degree distribution" caption="How many corpus papers receive k citations from other corpus papers (log scale)." deps={[dist]}
          method="Directed citation graph restricted to main-set papers of both institutes; in-degree counts citing papers inside the corpus only."
          option={() => ({ legend: { show: false }, tooltip: { trigger: "item", formatter: (p: any) => `in-degree ${p.value[0]}: ${p.value[1]} papers` }, // eslint-disable-line @typescript-eslint/no-explicit-any
            xAxis: { type: "log", name: "in-degree + 1", logBase: 10 }, yAxis: { type: "log", name: "papers", logBase: 10 },
            series: [{ type: "scatter", symbolSize: 8, data: dist.map(([d, n]) => [d + 1, n]), itemStyle: { color: cssVar("--seq-5"), borderColor: cssVar("--surface"), borderWidth: 2 } }] })}
          table={() => ({ columns: ["in-degree", "papers"], rows: dist })} />
      </div>
      <section className="card p-5">
        <h3 className="font-semibold text-[15px] mb-2">Cross-institute citation flow</h3>
        <table className="data tabnum"><thead><tr><th>Citing (source)</th><th>Cited (target)</th><th>Citations</th></tr></thead>
          <tbody>{(cn.cross_institute_flow as { source_inst: string; target_inst: string; edges: number }[]).map((r) => <tr key={r.source_inst + r.target_inst}><td>{r.source_inst}</td><td>{r.target_inst}</td><td>{fmt(r.edges)}</td></tr>)}</tbody></table>
      </section>
    </div>
  );
}
