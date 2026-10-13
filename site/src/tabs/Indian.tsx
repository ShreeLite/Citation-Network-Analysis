/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { indian, INSTS, PARTIAL_YEAR } from "../data";
import { useFilters } from "../filters";
import { ChartCard, cssVar, DataTable, fmt, instColor, Kpi, PartialNote } from "../components/ui";

const ch = createColumnHelper<any>();
const TYPES = ["IIT", "NIT", "IIIT", "IISER", "IISc-TIFR", "CSIR", "DAE", "Central University", "State University", "Private", "Other"];

export default function Indian() {
  const { f } = useFilters();
  const insts = f.inst === "both" ? INSTS : [f.inst];
  const conn = useMemo(() => (indian.connections as any[]).filter((r) => insts.includes(r.your_inst)), [insts.join()]); // eslint-disable-line react-hooks/exhaustive-deps
  const flow = useMemo(() => (indian.flow_by_year as any[]).filter((r) => insts.includes(r.your_inst) && r.year >= f.y0 && r.year <= f.y1), [insts.join(), f.y0, f.y1]); // eslint-disable-line react-hooks/exhaustive-deps
  const totals = insts.map((i) => {
    const r = flow.filter((x) => x.your_inst === i);
    const cin = r.reduce((s, x) => s + x.citations_in_from_indian, 0), cout = r.reduce((s, x) => s + x.citations_out_to_indian, 0);
    return { i, cin, cout, ratio: cout ? cin / cout : null, partners: conn.filter((x) => x.your_inst === i && x.shared_papers > 0).length };
  });
  const cols = useMemo(() => [
    ch.accessor("your_inst", { header: "Our inst." }), ch.accessor("partner_inst", { header: "Partner" }), ch.accessor("partner_type", { header: "Type" }),
    ch.accessor("shared_papers", { header: "Joint papers" }), ch.accessor("total_citations", { header: "Citations to us" }),
    ch.accessor("citations_given_to_partner", { header: "Our citations to them" }), ch.accessor("topic_jaccard", { header: "Topic Jaccard", cell: (c) => (c.getValue() === null || c.getValue() === undefined ? "—" : Number(c.getValue()).toFixed(3)) }),
  ], []);
  const byType = useMemo(() => TYPES.map((t) => ({ t, ...Object.fromEntries(insts.map((i) => [i, conn.filter((r) => r.your_inst === i && r.partner_type === t).reduce((s, r) => s + r.shared_papers, 0)])) })), [conn, insts.join()]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {totals.map((t) => [
          <Kpi key={`${t.i}r`} label={`${t.i} · impact ratio`} value={t.ratio === null ? "—" : `${t.ratio.toFixed(2)}`} sub={`${fmt(t.cin)} citations in / ${fmt(t.cout)} out (Indian, ${f.y0}–${f.y1})`} help="Citations received from other Indian institutions ÷ citations our papers give to them" />,
          <Kpi key={`${t.i}p`} label={`${t.i} · Indian co-author partners`} value={fmt(t.partners)} sub="institutions with ≥ 1 joint paper" />,
        ])}
      </div>
      <ChartCard title="Citation flow with other Indian institutions, by year" caption="Citations received from (in) and given to (out) Indian institutions other than our own." deps={[flow]} actions={<PartialNote />}
        method={`In: citing works with an Indian institution (not ours), by the citing work's year. Out: references from our papers to works with an Indian institution, by our paper's year. One count per (citation × partner institution). ${PARTIAL_YEAR} is partial.`}
        option={() => {
          const years = [...new Set(flow.map((r) => r.year))].sort();
          return { xAxis: { type: "category", data: years.map(String) }, yAxis: { type: "value" },
            series: insts.flatMap((i) => [
              { name: `${i} in`, type: "line", symbolSize: 7, symbol: "circle", legendIcon: "circle", lineStyle: { width: 2, color: instColor(i) }, itemStyle: { color: instColor(i) }, data: years.map((y) => flow.find((r) => r.your_inst === i && r.year === y)?.citations_in_from_indian ?? 0) },
              { name: `${i} out`, type: "line", symbolSize: 7, symbol: "emptyCircle", legendIcon: "emptyCircle", lineStyle: { width: 2, color: instColor(i), type: "solid", opacity: 0.45 }, itemStyle: { color: instColor(i), opacity: 0.6 }, data: years.map((y) => flow.find((r) => r.your_inst === i && r.year === y)?.citations_out_to_indian ?? 0) }]) };
        }}
        table={() => ({ columns: ["institute", "year", "in", "out", "in/out"], rows: flow.map((r) => [r.your_inst, r.year, r.citations_in_from_indian, r.citations_out_to_indian, r.impact_ratio_in_out]) })} />
      <div className="grid lg:grid-cols-2 gap-4">
        {insts.map((i) => (
          <ChartCard key={i} title={`${i}: top 10 citing Indian institutions`} caption="Citations received from works with each institution." deps={[]} height={360}
            method="Own institute excluded; an institution's lineage (parent/child IDs in OpenAlex) counts as itself."
            option={() => { const r = ((indian.top_citing[i] || []) as any[]).slice().reverse();
              return { legend: { show: false }, grid: { left: 8, right: 40 }, xAxis: { type: "value" }, yAxis: { type: "category", data: r.map((x) => x.partner_inst), axisLabel: { width: 220, overflow: "truncate" } },
                series: [{ type: "bar", data: r.map((x) => x.total_citations), itemStyle: { color: instColor(i), borderRadius: [0, 4, 4, 0] }, barMaxWidth: 14, label: { show: true, position: "right", color: cssVar("--ink-2") } }] }; }}
            table={() => ({ columns: ["partner", "type", "citations to us", "joint papers"], rows: ((indian.top_citing[i] || []) as any[]).map((x) => [x.partner_inst, x.partner_type, x.total_citations, x.shared_papers]) })} />))}
      </div>
      <ChartCard title="Joint papers by partner type (cross-cluster links)" caption="Co-authored papers with Indian institutions, grouped by institution type." deps={[byType]}
        method="Partner type from name rules plus a hand-checked mapping (data/external/partner_type_map.csv). A paper with two partners of one type counts once per partner."
        option={() => ({ xAxis: { type: "category", data: TYPES, axisLabel: { interval: 0, rotate: 25 } }, yAxis: { type: "value" },
          series: insts.map((i) => ({ name: i, type: "bar", data: byType.map((r) => (r as any)[i]), itemStyle: { color: instColor(i), borderRadius: [4, 4, 0, 0] } })) })}
        table={() => ({ columns: ["type", ...insts], rows: byType.map((r) => [r.t, ...insts.map((i) => (r as any)[i])]) })} />
      <DataTable title="All Indian partners (ranked by joint papers)" data={conn} columns={cols} filename="indian_connections_filtered.csv" pageSize={20} />
    </div>
  );
}
