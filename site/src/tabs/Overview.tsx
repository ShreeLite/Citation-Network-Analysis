import { useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import { findings, indian, INSTS, meta, PARTIAL_YEAR, YEAR_MAX, YEAR_MIN, type Paper } from "../data";
import { useFilters } from "../filters";
import { ChartCard, fmt, instColor, InstDot, Kpi, PartialNote, pct, Section } from "../components/ui";
import { headlines } from "./findingText";

export function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function quality(ps: Paper[]) {
  const j = ps.filter((p) => p.type === "journal"), c = ps.filter((p) => p.type === "conference");
  const jr = j.filter((p) => p.quartile), cr = c.filter((p) => ["A*", "A", "B", "C"].includes(p.core_rank || ""));
  return {
    q1: jr.length ? jr.filter((p) => p.quartile === "Q1").length / jr.length : null, nJ: j.length, nJr: jr.length,
    coreA: cr.length ? cr.filter((p) => p.core_rank === "A*" || p.core_rank === "A").length / cr.length : null, nC: c.length, nCr: cr.length,
  };
}

export function yearSeries(ps: Paper[], key: (p: Paper) => string, keys: string[], y0 = YEAR_MIN, y1 = YEAR_MAX) {
  const years = Array.from({ length: y1 - y0 + 1 }, (_, i) => y0 + i);
  const m: Record<string, number[]> = Object.fromEntries(keys.map((k) => [k, years.map(() => 0)]));
  for (const p of ps) { const k = key(p); if (m[k] && p.year >= y0 && p.year <= y1) m[k][p.year - y0]++; }
  return { years, m };
}

/** Papers per year per institute; a joint IIIT-H–IIIT-D paper counts for both. */
export function instYears(ps: Paper[], insts: string[], y0 = YEAR_MIN, y1 = YEAR_MAX) {
  const years = Array.from({ length: y1 - y0 + 1 }, (_, i) => y0 + i);
  const m: Record<string, number[]> = Object.fromEntries(insts.map((k) => [k, years.map(() => 0)]));
  for (const p of ps) for (const i of p.our_institutions.split(";")) if (m[i] && p.year >= y0 && p.year <= y1) m[i][p.year - y0]++;
  return { years, m };
}

export default function Overview() {
  const { f, fac, pap } = useFilters();
  const loc = useLocation();
  const k = useMemo(() => {
    const cites = pap.reduce((s, p) => s + (p.citations || 0), 0);
    const q = quality(pap);
    const hs = fac.map((x) => x.h_index_dataset).filter((x) => x !== undefined);
    const partners = new Set((indian.connections as { your_inst: string; partner_inst: string; shared_papers: number }[])
      .filter((r) => (f.inst === "both" || r.your_inst === f.inst) && r.shared_papers > 0).map((r) => r.partner_inst));
    return { cites, q, medH: median(hs), partners: partners.size };
  }, [pap, fac, f.inst]);

  const insts = f.inst === "both" ? INSTS : [f.inst];
  const side = insts.map((i) => {
    const ps = pap.filter((p) => p.our_institutions.split(";").includes(i));
    const fs = fac.filter((x) => x.institution === i);
    return { i, n: ps.length, fac: fs.length, cites: ps.reduce((s, p) => s + (p.citations || 0), 0), q: quality(ps),
      jShare: ps.length ? ps.filter((p) => p.type === "journal").length / ps.length : null, medH: median(fs.map((x) => x.h_index_dataset)) };
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-3">
        <Kpi label="Faculty" value={fmt(fac.length)} sub="core, in current filter" />
        <Kpi label="Papers" value={fmt(pap.length)} sub={`${f.y0}–${f.y1}`} />
        <Kpi label="Citations" value={fmt(k.cites)} sub="OpenAlex, at collection" />
        <Kpi label="Median h-index" value={fmt(k.medH)} sub="within 2016–2026 dataset" />
        <Kpi label={meta.quartile_source === "openalex_proxy" ? "Q1 share (proxy)" : "Q1 share"} value={pct(k.q.q1)} sub={`of ${fmt(k.q.nJr)} ranked journal papers${meta.quartile_source === "openalex_proxy" ? " · OpenAlex impact proxy, not SJR" : " · Scimago SJR"}`} />
        <Kpi label="CORE A*/A" value={pct(k.q.coreA)} sub={`of ${fmt(k.q.nCr)} ranked conf. papers`} />
        <Kpi label="Indian partners" value={fmt(k.partners)} sub="co-authoring institutions" />
      </div>

      <ChartCard
        title="Publications per year"
        caption={`Journal and conference papers by year and institute.`}
        method={`Main set: papers by core faculty within tenure or with an institute affiliation, deduplicated across OpenAlex, DBLP, Crossref and the IIIT-H portal. ${PARTIAL_YEAR} is partial (hatched).`}
        deps={[pap, f.inst]}
        actions={<PartialNote />}
        option={() => {
          const { years, m } = instYears(pap, insts);
          return {
            xAxis: { type: "category", data: years.map(String) },
            yAxis: { type: "value", name: "papers" },
            series: insts.map((i) => ({ name: i, type: "bar", barGap: "8%", itemStyle: { color: instColor(i), borderRadius: [4, 4, 0, 0] },
              data: m[i].map((v, idx) => years[idx] === PARTIAL_YEAR ? { value: v, itemStyle: { opacity: 0.45, decal: { symbol: "rect", dashArrayX: [1, 0], dashArrayY: [2, 4], rotation: Math.PI / 4 } } } : v) })),
          };
        }}
        table={() => { const { years, m } = instYears(pap, insts); return { columns: ["year", ...insts], rows: years.map((y, i) => [y, ...insts.map((k2) => m[k2][i])]) }; }}
      />

      <Section title="IIIT-H and IIIT-D side by side">
        <div className="grid md:grid-cols-2 gap-3">
          {side.map((s) => (
            <div key={s.i} className="card p-5">
              <div className="flex items-center gap-2 font-semibold"><InstDot inst={s.i} />{s.i === "IIIT-H" ? "IIIT Hyderabad — organised by research centres" : "IIIT Delhi — organised by departments"}</div>
              <dl className="grid grid-cols-3 gap-3 mt-4 text-[13px]">
                <div><dt className="muted">Faculty</dt><dd className="text-[20px] font-semibold">{fmt(s.fac)}</dd></div>
                <div><dt className="muted">Papers</dt><dd className="text-[20px] font-semibold">{fmt(s.n)}</dd></div>
                <div><dt className="muted">Citations</dt><dd className="text-[20px] font-semibold">{fmt(s.cites)}</dd></div>
                <div><dt className="muted">Journal share</dt><dd className="text-[20px] font-semibold">{pct(s.jShare, 0)}</dd></div>
                <div><dt className="muted">Q1 (ranked)</dt><dd className="text-[20px] font-semibold">{pct(s.q.q1, 0)}</dd></div>
                <div><dt className="muted">CORE A*/A</dt><dd className="text-[20px] font-semibold">{pct(s.q.coreA, 0)}</dd></div>
              </dl>
            </div>))}
        </div>
      </Section>

      <Section title="Three headline findings" intro="Each finding ends in a recommendation and names who would act on it. All seven are on the Findings tab.">
        <div className="grid md:grid-cols-3 gap-3">
          {headlines(findings).slice(0, 3).map((h) => (
            <Link key={h.id} to={{ pathname: "/findings", search: loc.search, hash: "" }} className="card p-5 block hover:shadow-md transition-shadow">
              <div className="text-[12px] uppercase tracking-wide muted">{h.kicker}</div>
              <div className="text-[26px] font-semibold mt-1">{h.number}</div>
              <div className="text-[13px] ink-2 mt-1">{h.numberLabel}</div>
              <p className="text-[13px] mt-3"><strong>{h.recommendation}</strong></p>
              <div className="text-[12px] muted mt-2">For: {h.audience}</div>
            </Link>))}
        </div>
      </Section>
    </div>
  );
}
