/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState, type ReactNode } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { findings, INSTS } from "../data";
import { ChartCard, cssVar, DataTable, fmt, instColor, pct } from "../components/ui";
import { headlines, type Headline } from "./findingText";

function Card({ h, children, note }: { h: Headline; children: ReactNode; note?: ReactNode }) {
  return (
    <article id={h.id} className="card p-5 sm:p-6 flex flex-col gap-4 scroll-mt-24">
      <header className="grid md:grid-cols-[1fr_auto] gap-3 items-start">
        <div>
          <div className="text-[12px] uppercase tracking-wide muted">Finding {h.kicker}</div>
          <h3 className="text-[18px] font-semibold mt-1">{h.question}</h3>
        </div>
        <div className="md:text-right">
          <div className="text-[34px] font-semibold leading-none">{h.number}</div>
        </div>
      </header>
      <p className="text-[13px] ink-2 -mt-2">{h.numberLabel}</p>
      {children}
      <footer className="border-t hairline pt-3 flex flex-col gap-1">
        <p className="text-[14px]"><strong>Recommendation: {h.recommendation}</strong></p>
        <p className="text-[12px] muted">Who acts: {h.audience}</p>
        {note && <div className="text-[12px] muted">{note}</div>}
      </footer>
    </article>
  );
}

const pairCol = createColumnHelper<any>();

export default function Findings() {
  const F = findings;
  const H = headlines(F);
  const [scope, setScope] = useState("all");
  const pairs = useMemo(() => (F.f4.pairs as any[]).filter((p) => scope === "all" || p.scope === scope), [scope, F]);
  const pairCols = useMemo(() => [
    pairCol.accessor("faculty_a", { header: "Faculty A" }), pairCol.accessor("unit_a", { header: "Unit A" }), pairCol.accessor("institution_a", { header: "Inst. A" }),
    pairCol.accessor("faculty_b", { header: "Faculty B" }), pairCol.accessor("unit_b", { header: "Unit B" }), pairCol.accessor("institution_b", { header: "Inst. B" }),
    pairCol.accessor("topic_jaccard", { header: "Topic Jaccard" }), pairCol.accessor("tier", { header: "Tier" }), pairCol.accessor("shared_coauthors", { header: "Shared co-authors" }), pairCol.accessor("shared_topic_names", { header: "Shared topics", cell: (c) => <span className="block max-w-[360px]">{c.getValue()}</span> }),
  ], []);
  const apCols = useMemo(() => [
    pairCol.accessor("institution", { header: "Inst." }), pairCol.accessor("unit", { header: "Unit" }), pairCol.accessor("name", { header: "Articulation point" }),
    pairCol.accessor("component_size", { header: "Component size" }), pairCol.accessor("cut_off", { header: "Faculty cut off if they leave" }),
  ], []);

  return (
    <div className="flex flex-col gap-6">
      <nav className="card p-3 flex flex-wrap gap-2 text-[13px] no-print" aria-label="Findings">{H.map((h) => <a key={h.id} className="chip" href={`#${h.id}`} onClick={(e) => { e.preventDefault(); document.getElementById(h.id)?.scrollIntoView({ behavior: "smooth" }); }}>{h.kicker}</a>)}</nav>

      {/* 1 */}
      <Card h={H[0]} note={<>Thresholds: {INSTS.map((i) => { const t = F.f1.thresholds[i] || {}; return `${i}: betweenness ≥ ${t.betweenness_threshold?.toFixed(4)} (top ${Math.round((1 - (t.betweenness_percentile ?? 0.85)) * 100)}%) and degree ≤ ${t.degree_threshold} (not in the top quarter; median ${t.degree_median}); ${t.n_flagged_strict_median_rule} would also pass the stricter below-median rule; n = ${t.n_connected} connected faculty`; }).join(" · ")}. Try it live on the Collaboration Network tab (click-to-remove).</>}>
        <ChartCard title="Betweenness vs degree" caption="Every faculty member; flagged bridges outlined. Within-institute networks." deps={[]} height={380}
          method="Betweenness: normalised shortest-path betweenness on each institute's unweighted faculty co-authorship graph. LCC drop = people disconnected from the largest connected group when the person is removed."
          option={() => ({ tooltip: { trigger: "item", formatter: (p: any) => `${p.data.name} (${p.data.unit})<br/>degree ${p.data.value[0]}, betweenness ${p.data.value[1].toFixed(4)}${p.data.flagged ? "<br/><b>flagged bridge</b>" : ""}` },
            xAxis: { type: "value", name: "degree (co-authors in institute)" }, yAxis: { type: "value", name: "betweenness" },
            series: INSTS.map((i) => ({ name: i, type: "scatter", itemStyle: { color: instColor(i) }, symbolSize: (v: any, p: any) => (p.data.flagged ? 14 : 9),
              data: (F.f1.scatter as any[]).filter((s) => s.institution === i).map((s) => ({ value: [s.degree, s.betweenness], name: s.name, unit: s.unit, flagged: s.flagged,
                itemStyle: { color: instColor(i), borderColor: s.flagged ? cssVar("--ink") : cssVar("--surface"), borderWidth: 2, opacity: s.flagged ? 1 : 0.7 } })) })) })}
          table={() => ({ columns: ["name", "institute", "unit", "degree", "betweenness", "flagged"], rows: (F.f1.scatter as any[]).map((s) => [s.name, s.institution, s.unit, s.degree, s.betweenness.toFixed(4), s.flagged ? "yes" : ""]) })} />
        <div className="overflow-x-auto"><table className="data tabnum"><thead><tr><th>Flagged</th><th>Inst.</th><th>Unit</th><th>Degree</th><th>Betweenness</th><th>Largest group: before → after</th><th>Drop</th></tr></thead>
          <tbody>{(F.f1.table as any[]).map((r) => <tr key={r.faculty_id}><td>{r.name}</td><td>{r.institution}</td><td>{r.unit}</td><td>{r.degree}</td><td>{r.betweenness.toFixed(4)}</td><td>{r.lcc_before} → {r.lcc_after}</td><td>{r.lcc_drop} ({pct(r.lcc_drop_pct, 0)})</td></tr>)}</tbody></table></div>
      </Card>

      {/* 2 */}
      <Card h={H[1]}>
        <ChartCard title="Articulation points per unit" caption="Single faculty whose departure splits the unit's internal co-authorship network. Unit size in the table." deps={[]} height={Math.max(260, 26 * F.f2.per_unit.length)}
          method="Articulation points of each unit's internal network (unit members only, primary unit). 'Cut off' = faculty who lose their link to the rest of their component."
          option={() => { const rows = [...(F.f2.per_unit as any[])].sort((a, b) => a.articulation_points - b.articulation_points);
            return { legend: { show: false }, grid: { left: 8, right: 30 }, xAxis: { type: "value", minInterval: 1 },
              yAxis: { type: "category", data: rows.map((r) => `${r.unit} (${r.institution}, n=${r.n_faculty})`), axisLabel: { width: 220, overflow: "truncate" } },
              series: [{ type: "bar", data: rows.map((r) => ({ value: r.articulation_points, itemStyle: { color: instColor(r.institution), borderRadius: [0, 4, 4, 0] } })), barMaxWidth: 14, label: { show: true, position: "right", color: cssVar("--ink-2") } }] }; }}
          table={() => ({ columns: ["institute", "unit", "faculty", "links", "isolated", "components", "largest component", "articulation points"], rows: (F.f2.per_unit as any[]).map((r) => [r.institution, r.unit, r.n_faculty, r.n_edges, r.isolated, r.components, r.largest_component, r.articulation_points]) })} />
        <DataTable data={F.f2.points} columns={apCols} filename="finding2_articulation_points.csv" pageSize={10} title="Who they are" />
      </Card>

      {/* 3 */}
      <Card h={H[2]} note="Year 1 = joining year; degree is cumulative distinct co-authors among same-institute core faculty. Only people whose 3-year window ends by 2025 are counted (2026 is partial). Joining year from the faculty page/CV, else the first institute-affiliated paper (marked inferred).">
        <ChartCard title="New-joiner integration curve" caption="Median internal co-authors in years 1–3 after joining, and share still at zero, by institute." deps={[]}
          method="Faculty who joined in 2016 or later with a known joining year; n per group in the table."
          option={() => { const s = (F.f3.summary as any[]).filter((r) => r.unit === "All units");
            return { xAxis: { type: "category", data: ["Year 1", "Year 2", "Year 3"] }, yAxis: { type: "value", name: "median internal co-authors", minInterval: 1 },
              series: s.map((r) => ({ name: `${r.institution} (n=${r.n})`, type: "line", symbolSize: 8, lineStyle: { width: 2, color: instColor(r.institution) }, itemStyle: { color: instColor(r.institution) },
                data: [r.median_deg_y1, r.median_deg_y2, r.median_deg_y3], endLabel: { show: true, formatter: `${pct(r.share_zero_after_3y, 0)} at zero`, color: cssVar("--ink-2") } })) }; }}
          table={() => ({ columns: ["institute", "unit", "n", "median y1", "median y2", "median y3", "share at zero after 3y"], rows: (F.f3.summary as any[]).map((r) => [r.institution, r.unit, r.n, r.median_deg_y1, r.median_deg_y2, r.median_deg_y3, pct(r.share_zero_after_3y, 0)]) })} />
      </Card>

      {/* 4 */}
      <Card h={H[3]} note={`Topic sets: OpenAlex topics appearing in ≥ 2 of a person's papers (all topics for people with < 5 papers); only people with ≥ 3 topics are compared (smaller sets make Jaccard trivially high); ${F.f4.n_faculty_with_topics} faculty have topic sets. Pairs that already have a joint paper are excluded. Tier 1 = no shared co-author either (the strict definition); tier 2 = already connected through a shared co-author (papers with > 25 authors ignored).`}>
        <div className="flex flex-wrap gap-2 text-[13px] no-print">Show:
          {["all", "cross-institute", "within IIIT-H", "within IIIT-D"].map((s) => <button key={s} className={`btn ${scope === s ? "btn-primary" : ""}`} onClick={() => setScope(s)}>{s} {s === "all" ? `(${(F.f4.pairs as any[]).length})` : `(${F.f4.counts[s] || 0})`}</button>)}</div>
        <DataTable title="Missed collaborations" data={pairs} columns={pairCols} filename="missed_collaborations.csv" pageSize={15} />
      </Card>

      {/* 5 */}
      <Card h={H[4]} note="Within-unit = all faculty authors in the same unit; cross-unit = faculty from ≥ 2 units (or both institutes); single-faculty papers excluded. Compared year by year only, never across years.">
        <ChartCard title="Median citations: cross-unit vs within-unit, same year" caption="Each point compares papers from the same publication year." deps={[]}
          method="OpenAlex citations at collection date. Pooled figure divides each paper's citations by the median of all papers from its year before comparing groups."
          option={() => { const r = F.f5.by_year as any[];
            return { xAxis: { type: "category", data: r.map((x) => String(x.year)) }, yAxis: { type: "value", name: "median citations" },
              series: [{ name: "cross-unit", type: "line", symbolSize: 8, data: r.map((x) => x.cross_median), lineStyle: { width: 2, color: cssVar("--conference") }, itemStyle: { color: cssVar("--conference") } },
                       { name: "within-unit", type: "line", symbolSize: 8, data: r.map((x) => x.within_median), lineStyle: { width: 2, color: cssVar("--journal") }, itemStyle: { color: cssVar("--journal") } }] }; }}
          table={() => ({ columns: ["year", "cross-unit median", "n", "within-unit median", "n", "partial"], rows: (F.f5.by_year as any[]).map((x) => [x.year, x.cross_median, x.cross_n, x.within_median, x.within_n, x.partial ? "yes" : ""]) })} />
      </Card>

      {/* 6 */}
      <Card h={H[5]} note="Population = all core faculty of the institute, including those with zero papers that year. Links = co-authorship degree within the institute (whole period). Gini is the secondary measure (0 = equal, 1 = one person has everything).">
        <ChartCard title="Share of citations held by the top 10% of faculty, by publication year" caption="One line per institute; papers counted in the year they were published." deps={[]}
          method="Top-10% share = output of the ⌈10% × faculty⌉ highest-output people ÷ total. Citations of recent papers are still accruing."
          option={() => { const rows = (F.f6.rows as any[]).filter((r) => r.year !== "all");
            const years = [...new Set(rows.map((r) => r.year))];
            return { xAxis: { type: "category", data: years.map(String) }, yAxis: { type: "value", max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
              tooltip: { trigger: "axis", valueFormatter: (v: number) => pct(v, 0) },
              series: INSTS.map((i) => ({ name: i, type: "line", symbolSize: 8, lineStyle: { width: 2, color: instColor(i) }, itemStyle: { color: instColor(i) }, data: years.map((y) => rows.find((r) => r.institution === i && r.year === y)?.top10_share_citations ?? null) })) }; }}
          table={() => ({ columns: ["institute", "year", "faculty", "top10% papers", "top10% citations", "top10% links", "Gini papers", "Gini citations"], rows: (F.f6.rows as any[]).map((r) => [r.institution, r.year, r.n_faculty, pct(r.top10_share_papers, 0), pct(r.top10_share_citations, 0), r.top10_share_links !== undefined ? pct(r.top10_share_links, 0) : "", fmt(r.gini_papers), fmt(r.gini_citations)]) })} />
      </Card>

      {/* 7 */}
      <Card h={H[6]} note="Citations counted as (citing work × partner institution); own institute excluded. Flag: top 10% of partners by citations to us and ≤ 1 co-authored paper.">
        <ChartCard title="Citations to us vs co-authored papers, per Indian institute" caption="Each dot is an Indian institute; top-left = uses our work but rarely works with us." deps={[]} height={400}
          method="x: co-authored main-set papers; y: citations received from works with that institution. Log scales (value + 1)."
          option={() => ({ tooltip: { trigger: "item", formatter: (p: any) => `${p.data.name}<br/>${p.data.value[1] - 1} citations · ${p.data.value[0] - 1} joint papers` },
            xAxis: { type: "log", name: "co-authored papers + 1" }, yAxis: { type: "log", name: "citations to us + 1" },
            series: INSTS.map((i) => ({ name: i, type: "scatter", itemStyle: { color: instColor(i) }, data: ((F.f7[i]?.partners || []) as any[]).map((r) => ({ name: r.partner_inst, value: [r.shared_papers + 1, r.total_citations + 1],
              itemStyle: { color: instColor(i), borderColor: r.cites_us_not_collab ? cssVar("--ink") : cssVar("--surface"), borderWidth: 2 } })), symbolSize: 10 })) })}
          table={() => ({ columns: ["institute", "partner", "type", "citations to us", "joint papers", "flag"], rows: INSTS.flatMap((i) => ((F.f7[i]?.partners || []) as any[]).map((r) => [i, r.partner_inst, r.partner_type, r.total_citations, r.shared_papers, r.cites_us_not_collab ? "yes" : ""])) })} />
        <div className="grid md:grid-cols-2 gap-3">{INSTS.map((i) => (
          <div key={i}><h4 className="font-semibold text-[14px] mb-1">{i}: MoU targets</h4>
            <table className="data tabnum"><thead><tr><th>Institute</th><th>Type</th><th>Citations</th><th>Joint</th></tr></thead>
              <tbody>{((F.f7[i]?.flagged || []) as any[]).slice(0, 10).map((r) => <tr key={r.partner_inst}><td>{r.partner_inst}</td><td>{r.partner_type}</td><td>{r.total_citations}</td><td>{r.shared_papers}</td></tr>)}</tbody></table></div>))}</div>
      </Card>
    </div>
  );
}
