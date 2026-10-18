import { useMemo, useState } from "react";
import { INSTS, meta } from "../data";
import { useFilters } from "../filters";
import { ChartCard, cssVar, fmt, instColor, Kpi, pct } from "../components/ui";
import { quality } from "./Overview";
import { venueName } from "./Publications";

const QS = ["Q1", "Q2", "Q3", "Q4"];
const CORE = ["A*", "A", "B", "C"];
const IF_THRESHOLDS = [{ label: "All", value: 0 }, { label: "IF > 5", value: 5 }, { label: "IF > 10", value: 10 }] as const;

export default function Venues() {
  const { f, pap } = useFilters();
  const insts = f.inst === "both" ? INSTS : [f.inst];
  const [q1Only, setQ1Only] = useState(false);
  const [ifMin, setIfMin] = useState(0);

  const filteredPap = useMemo(() => pap.filter((p) => {
    if (q1Only && p.quartile !== "Q1") return false;
    if (ifMin > 0 && (!p.impact_factor || p.impact_factor <= ifMin)) return false;
    return true;
  }), [pap, q1Only, ifMin]);
  const by = useMemo(() => Object.fromEntries(insts.map((i) => {
    const ps = filteredPap.filter((p) => p.our_institutions.split(";").includes(i));
    const j = ps.filter((p) => p.type === "journal"), c = ps.filter((p) => p.type === "conference");
    const qd = QS.map((q) => j.filter((p) => p.quartile === q).length);
    const cd = CORE.map((r) => c.filter((p) => p.core_rank === r).length);
    const tops = (t: string) => {
      const m: Record<string, { n: number; rank: string; avgIf: number[] }> = {};
      for (const p of ps.filter((x) => x.type === t)) { const v = venueName(p); if (!m[v]) m[v] = { n: 0, rank: "", avgIf: [] }; m[v].n++; m[v].rank = (t === "journal" ? p.quartile : p.core_rank) || m[v].rank; if (p.impact_factor) m[v].avgIf.push(p.impact_factor); }
      return Object.entries(m).sort((a, b) => b[1].n - a[1].n).slice(0, 5);
    };
    return [i, { q: quality(ps), qd, cd, nJ: j.length, nC: c.length, unJ: j.length - qd.reduce((a, b) => a + b, 0), unC: c.length - cd.reduce((a, b) => a + b, 0), topJ: tops("journal"), topC: tops("conference") }];
  })), [filteredPap, insts.join()]); // eslint-disable-line react-hooks/exhaustive-deps

  // share chart: one axis (%), one bar per rank, institutes side by side
  const shareOpt = (cats: string[], key: "qd" | "cd", n: "nJ" | "nC") => () => ({
    xAxis: { type: "category", data: cats }, yAxis: { type: "value", axisLabel: { formatter: (v: number) => `${v}%` } },
    tooltip: { trigger: "axis", valueFormatter: (v: number) => `${v.toFixed(1)}%` },
    series: insts.map((i) => ({ name: i, type: "bar", itemStyle: { color: instColor(i), borderRadius: [4, 4, 0, 0] },
      data: by[i][key].map((v: number) => (by[i][n] ? (100 * v) / by[i][n] : 0)) })),
  });

  const ifStats = useMemo(() => {
    const withIf = pap.filter((p) => p.impact_factor != null && p.impact_factor > 0);
    return { total: withIf.length, gt5: withIf.filter((p) => p.impact_factor! > 5).length, gt10: withIf.filter((p) => p.impact_factor! > 10).length };
  }, [pap]);

  return (
    <div className="flex flex-col gap-5">
      <div className="card p-3 flex flex-wrap items-center gap-3 text-[13px] no-print" role="region" aria-label="Quality filters">
        <span className="font-semibold">Quality filters:</span>
        <button className={`btn ${q1Only ? "btn-primary" : ""}`} onClick={() => setQ1Only(!q1Only)}>{q1Only ? "Q1 only ✓" : "Q1 only"}</button>
        {IF_THRESHOLDS.map((t) => (
          <button key={t.value} className={`btn ${ifMin === t.value ? "btn-primary" : ""}`} onClick={() => setIfMin(t.value)}>{t.label}</button>
        ))}
        {(q1Only || ifMin > 0) && <button className="btn" onClick={() => { setQ1Only(false); setIfMin(0); }}>Clear quality filters</button>}
        {(q1Only || ifMin > 0) && <span className="muted">{fmt(filteredPap.length)} of {fmt(pap.length)} papers shown</span>}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {insts.map((i) => [
          <Kpi key={`${i}q`} label={`${i} · Q1 share${meta.quartile_source === "openalex_proxy" ? " (proxy)" : ""}`} value={pct(by[i].q.q1)} sub={`of ${fmt(by[i].q.nJr)} ranked journal papers (${fmt(by[i].nJ)} journal papers)`} />,
          <Kpi key={`${i}c`} label={`${i} · CORE A*/A`} value={pct(by[i].q.coreA)} sub={`of ${fmt(by[i].q.nCr)} ranked conference papers (${fmt(by[i].nC)})`} />,
        ])}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        <Kpi label="Papers with IF data" value={fmt(ifStats.total)} sub={`of ${fmt(pap.length)} total papers`} />
        <Kpi label="Papers in IF > 5 venues" value={fmt(ifStats.gt5)} sub={`${pap.length ? ((100 * ifStats.gt5) / pap.length).toFixed(1) : 0}% of papers`} />
        <Kpi label="Papers in IF > 10 venues" value={fmt(ifStats.gt10)} sub={`${pap.length ? ((100 * ifStats.gt10) / pap.length).toFixed(1) : 0}% of papers`} />
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title={meta.quartile_source === "openalex_proxy" ? "Journal quartiles (proxy)" : "Journal quartiles"} caption={meta.quartile_source === "openalex_proxy" ? "PROXY: quartile of each journal's OpenAlex 2-year mean citedness within its field — Scimago SJR files were not available at build time." : "Share of each institute's journal papers in Scimago Q1–Q4 (unranked shown in the table)."} deps={[by]}
          method="Scimago SJR best quartile across the journal's subject categories, for the paper's publication year (nearest available year when missing). Joined by print or electronic ISSN."
          option={shareOpt(QS, "qd", "nJ")}
          table={() => ({ columns: ["institute", ...QS, "unranked", "journal papers"], rows: insts.map((i) => [i, ...by[i].qd, by[i].unJ, by[i].nJ]) })} />
        <ChartCard title="CORE conference ranks" caption="Share of each institute's conference papers at CORE A*, A, B, C (unranked in the table)." deps={[by]}
          method="CORE edition in force at publication (latest edition ≤ paper year, else earliest). Matched by acronym (confirmed by title), then fuzzy title ≥ 92; manual overrides in data/external/core_overrides.csv."
          option={shareOpt(CORE, "cd", "nC")}
          table={() => ({ columns: ["institute", ...CORE, "unranked", "conference papers"], rows: insts.map((i) => [i, ...by[i].cd, by[i].unC, by[i].nC]) })} />
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        {insts.map((i) => (
          <section key={i} className="card p-5">
            <h3 className="font-semibold text-[15px]" style={{ color: "var(--ink)" }}><span className="dot mr-2" style={{ background: instColor(i) }} />{i}: top venues</h3>
            {(["topJ", "topC"] as const).map((k) => (
              <div key={k} className="mt-3">
                <div className="text-[12px] uppercase tracking-wide muted mb-1">{k === "topJ" ? "Journals (quartile)" : "Conferences (CORE)"}</div>
                <table className="data tabnum"><thead><tr><th>Venue</th><th>{k === "topJ" ? "Q" : "CORE"}</th>{k === "topJ" && <th>IF</th>}<th className="text-right">Papers</th></tr></thead><tbody>{by[i][k].map(([v, x]: [string, { n: number; rank: string; avgIf: number[] }]) => (
                  <tr key={v}><td>{v}</td><td className="muted">{x.rank || "—"}</td>{k === "topJ" && <td className="muted">{x.avgIf.length ? (x.avgIf.reduce((a, b) => a + b, 0) / x.avgIf.length).toFixed(1) : "—"}</td>}<td className="text-right">{x.n}</td></tr>))}</tbody></table>
              </div>))}
          </section>))}
      </div>
      <p className="text-[12px] muted" style={{ color: cssVar("--muted") }}>Journals are a minority of IIIT output, so Q1 share is always shown next to the CORE A*/A share of conference papers.</p>
    </div>
  );
}
