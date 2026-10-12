import { central, INSTS } from "../data";
import { ChartCard, cssVar, fmt, instColor, InstDot, Section } from "../components/ui";

interface CQ {
  n_faculty: number; n_active: number; n_edges: number; n_units: number; n_communities: number;
  nmi_units_vs_communities: number; modularity_communities: number; modularity_units: number; avg_clustering: number;
  cross_unit_share_links: number; cross_unit_share_weighted: number;
  null_model: { observed: Record<string, number>; null_mean: Record<string, number>; null_sd: Record<string, number>; z: Record<string, number>; ratio: Record<string, number>; samples: number };
  unit_labels: string[]; community_labels: string[]; matrix: number[][]; unit_sizes: Record<string, number>;
}

const n3 = (v: number | null | undefined) => (v === null || v === undefined || Number.isNaN(v) ? "—" : v.toFixed(3));

function verdict(c: CQ): string {
  const nmi = c.nmi_units_vs_communities;
  const z = c.null_model.z?.cross_unit_share;
  if (nmi >= 0.5) return "Detected communities largely mirror the official units, and cross-unit links are " + (z !== undefined && z < -2 ? "rarer than chance — the org chart is a barrier." : "not much rarer than chance.");
  if (nmi >= 0.25) return "Communities partly follow the official units.";
  return "Communities do not follow the official units — the org chart is not what shapes collaboration.";
}

export default function Central() {
  const C = central as Record<string, CQ>;
  const metrics: [string, keyof CQ | string, string][] = [
    ["NMI (communities vs units)", "nmi_units_vs_communities", "0 = unrelated, 1 = identical partitions"],
    ["Modularity of detected communities", "modularity_communities", "Louvain, weighted"],
    ["Modularity of official units", "modularity_units", "how well units work as communities"],
    ["Average clustering", "avg_clustering", "unweighted"],
    ["Cross-unit share of links", "cross_unit_share_links", "co-author pairs from different units"],
  ];
  return (
    <div className="flex flex-col gap-6">
      <Section title="Does the org chart shape who works with whom?"
        intro="IIIT-H is organised by research centres, IIIT-D by departments. We detect communities in each institute's faculty co-authorship network and ask how closely they match the official units, and whether collaborations cross unit boundaries more or less than a degree-preserving random network would.">
        <div className="grid md:grid-cols-2 gap-3">
          {INSTS.map((i) => C[i] && (
            <div key={i} className="card p-5">
              <div className="flex items-center gap-2 font-semibold"><InstDot inst={i} />{i} · {C[i].n_units} {i === "IIIT-H" ? "centres" : "departments"} · {C[i].n_communities} communities</div>
              <div className="text-[32px] font-semibold mt-2">{n3(C[i].nmi_units_vs_communities)}</div>
              <div className="text-[13px] ink-2">NMI between detected communities and official units ({C[i].n_active} faculty with ≥1 internal co-author of {C[i].n_faculty}; {C[i].n_edges} links)</div>
              <p className="text-[13px] mt-3"><strong>{verdict(C[i])}</strong></p>
            </div>))}
        </div>
      </Section>

      <section className="card p-5 overflow-x-auto">
        <h3 className="font-semibold text-[15px] mb-2">Side-by-side metrics with null-model comparison</h3>
        <table className="data tabnum">
          <thead><tr><th>Metric</th>{INSTS.map((i) => <th key={i}>{i}</th>)}<th>Note</th></tr></thead>
          <tbody>
            {metrics.map(([label, key, note]) => (
              <tr key={label}><td>{label}</td>{INSTS.map((i) => <td key={i}>{n3(C[i]?.[key as keyof CQ] as number)}</td>)}<td className="muted">{note}</td></tr>))}
            {(["clustering", "modularity", "cross_unit_share"] as const).map((k) => (
              <tr key={k}><td>{k.replace(/_/g, " ")} vs random</td>
                {INSTS.map((i) => { const nm = C[i]?.null_model; return <td key={i}>{nm?.samples ? `${n3(nm.observed[k])} vs ${n3(nm.null_mean[k])} ± ${n3(nm.null_sd[k])} (z = ${nm.z[k]?.toFixed(1)}, ${nm.ratio[k]?.toFixed(2)}× random)` : "—"}</td>; })}
                <td className="muted">{C["IIIT-H"]?.null_model?.samples} degree-preserving rewirings</td></tr>))}
          </tbody>
        </table>
      </section>

      <ChartCard title="Observed vs random" caption="Each metric as a multiple of its mean in degree-preserving random networks (1.0 = what chance gives)." deps={[]}
        method="Null model: double-edge swaps (10 × edges per sample) keep every person's number of co-authors fixed but scramble who they are; Louvain re-run on each sample."
        option={() => {
          const ks = ["clustering", "modularity", "cross_unit_share"];
          return { xAxis: { type: "category", data: ks.map((k) => k.replace(/_/g, " ")) }, yAxis: { type: "value", name: "× random" },
            series: [...INSTS.map((i) => ({ name: i, type: "bar", itemStyle: { color: instColor(i), borderRadius: [4, 4, 0, 0] }, data: ks.map((k) => C[i]?.null_model?.ratio?.[k] ?? null) })),
              { name: "random = 1", type: "line", data: ks.map(() => 1), symbol: "none", lineStyle: { color: cssVar("--muted"), width: 1 }, tooltip: { show: false } }] };
        }}
        table={() => ({ columns: ["metric", ...INSTS.map((i) => `${i} × random`), ...INSTS.map((i) => `${i} z`)], rows: ["clustering", "modularity", "cross_unit_share"].map((k) => [k, ...INSTS.map((i) => C[i]?.null_model?.ratio?.[k]), ...INSTS.map((i) => C[i]?.null_model?.z?.[k])]) })} />

      <div className="grid xl:grid-cols-2 gap-4">
        {INSTS.map((i) => C[i] && (
          <ChartCard key={i} title={`${i}: official unit × detected community`} caption="Faculty counts; a diagonal-looking pattern means communities follow units." deps={[]} height={Math.max(260, 34 * C[i].unit_labels.length + 80)}
            method="Rows: primary unit from the official site (group size in the table). Columns: Louvain communities, largest first. Faculty with no internal co-author excluded."
            option={() => {
              const m = C[i].matrix; const max = Math.max(1, ...m.flat());
              return { legend: { show: false }, grid: { left: 8, right: 16, top: 10, bottom: 30 }, tooltip: { trigger: "item", formatter: (p: any) => `${C[i].unit_labels[p.value[1]]} · ${C[i].community_labels[p.value[0]]}: ${p.value[2]} faculty` }, // eslint-disable-line @typescript-eslint/no-explicit-any
                xAxis: { type: "category", data: C[i].community_labels }, yAxis: { type: "category", data: C[i].unit_labels },
                visualMap: { show: false, min: 0, max, inRange: { color: [cssVar("--surface-2"), instColor(i)] } },
                series: [{ type: "heatmap", data: m.flatMap((row, y) => row.map((v, x) => [x, y, v])), label: { show: true, color: cssVar("--ink"), formatter: (p: any) => (p.value[2] ? p.value[2] : "") }, itemStyle: { borderColor: cssVar("--surface"), borderWidth: 2 } }] }; // eslint-disable-line @typescript-eslint/no-explicit-any
            }}
            table={() => ({ columns: ["unit", "unit size", ...C[i].community_labels], rows: C[i].unit_labels.map((u, y) => [u, C[i].unit_sizes[u], ...C[i].matrix[y]]) })} />))}
      </div>

      <section className="card p-5">
        <h3 className="font-semibold text-[15px]">What to do with this</h3>
        <p className="text-[14px] mt-2"><strong>If clusters mirror units and cross-unit collaboration is rarer than chance, the org chart is the barrier: joint PhD supervision across units and cross-unit seed grants are the lever. If communities ignore the units, restructuring units will not change collaboration — invest in people and topics instead.</strong></p>
        <p className="text-[12px] muted mt-2">Audience: institute leadership and the academic council. Group sizes: {INSTS.map((i) => `${i} ${fmt(C[i]?.n_active)} active of ${fmt(C[i]?.n_faculty)}`).join(" · ")}.</p>
      </section>
    </div>
  );
}
