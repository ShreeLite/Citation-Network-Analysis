import { useMemo } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { INSTS, PARTIAL_YEAR, type Paper } from "../data";
import { useFilters } from "../filters";
import { ChartCard, cssVar, DataTable, fmt, PartialNote, Section, typeColor } from "../components/ui";
import { yearSeries } from "./Overview";

const ch = createColumnHelper<Paper>();
export const doiLink = (d?: string | null) => (d ? <a className="link" href={`https://doi.org/${d}`} target="_blank" rel="noreferrer">{d}</a> : "—");

export function venueName(p: Paper) { return p.acronym || p.journal_name || "—"; }

export default function Publications() {
  const { f, pap } = useFilters();
  const types = (["journal", "conference", "preprint"] as const).filter((t) => f.types[t]);
  const top = useMemo(() => [...pap].sort((a, b) => (b.citations || 0) - (a.citations || 0)).slice(0, 10), [pap]);
  const venues = useMemo(() => {
    const out: Record<string, Record<string, number>> = {};
    for (const t of ["journal", "conference"]) {
      const c: Record<string, number> = {};
      for (const p of pap) if (p.type === t) c[venueName(p)] = (c[venueName(p)] || 0) + 1;
      out[t] = Object.fromEntries(Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, 10));
    }
    return out;
  }, [pap]);
  const cols = useMemo(() => [
    ch.accessor("title", { header: "Title", cell: (c) => <span className="block max-w-[520px]">{c.getValue()}</span> }),
    ch.accessor("year", { header: "Year" }),
    ch.accessor("type", { header: "Type" }),
    ch.accessor((p) => venueName(p), { id: "venue", header: "Venue" }),
    ch.accessor("our_institutions", { header: "Institute" }),
    ch.accessor("citations", { header: "Citations", cell: (c) => fmt(c.getValue()) }),
    ch.accessor("quartile", { header: "Q", cell: (c) => c.getValue() || "—" }),
    ch.accessor("core_rank", { header: "CORE", cell: (c) => c.getValue() || "—" }),
    ch.accessor("doi", { header: "DOI", cell: (c) => doiLink(c.getValue()) }),
  ], []);

  return (
    <div className="flex flex-col gap-5">
      <ChartCard title="Output by year and type" caption="Papers per year, split by journal, conference and (optionally) preprint." deps={[pap, types.join()]}
        method={`Type from DBLP record type (wins for CS venues), else OpenAlex source type, Crossref type, IIIT-H portal. Preprints are arXiv-only works with no published version; off by default. ${PARTIAL_YEAR} is partial.`}
        actions={<PartialNote />}
        option={() => {
          const { years, m } = yearSeries(pap, (p) => p.type, types);
          return { xAxis: { type: "category", data: years.map(String) }, yAxis: { type: "value" },
            series: types.map((t) => ({ name: t, type: "bar", stack: "t", itemStyle: { color: typeColor(t), borderColor: cssVar("--surface"), borderWidth: 1 },
              data: m[t].map((v, i) => (years[i] === PARTIAL_YEAR ? { value: v, itemStyle: { opacity: 0.45 } } : v)) })) };
        }}
        table={() => { const { years, m } = yearSeries(pap, (p) => p.type, types); return { columns: ["year", ...types], rows: years.map((y, i) => [y, ...types.map((t) => m[t][i])]) }; }} />

      <div className="grid lg:grid-cols-2 gap-4">
        {(["journal", "conference"] as const).map((t) => (
          <ChartCard key={t} title={`Top ${t === "journal" ? "journals" : "conferences"}`} caption={`Ten most frequent ${t} venues in the current filter.`} deps={[venues]} height={340}
            method="Venue names normalised: proceedings titles mapped to a canonical name + acronym (data/external/venue_map.csv, top 150 hand-checked)."
            option={() => { const e = Object.entries(venues[t]).reverse(); return { grid: { left: 8, right: 30 }, tooltip: { trigger: "item" }, xAxis: { type: "value" },
              yAxis: { type: "category", data: e.map((x) => x[0]), axisLabel: { width: 180, overflow: "truncate" } }, legend: { show: false },
              series: [{ type: "bar", data: e.map((x) => x[1]), itemStyle: { color: typeColor(t), borderRadius: [0, 4, 4, 0] }, barMaxWidth: 16, label: { show: true, position: "right", color: cssVar("--ink-2") } }] }; }}
            table={() => ({ columns: ["venue", "papers"], rows: Object.entries(venues[t]) })} />))}
      </div>

      <Section title="Ten most-cited papers" intro="In the current filter. Citation counts from OpenAlex at the collection date.">
        <div className="card overflow-x-auto">
          <table className="data tabnum">
            <thead><tr><th>#</th><th>Title</th><th>Venue</th><th>Year</th><th>Institute</th><th>Citations</th><th>DOI</th></tr></thead>
            <tbody>{top.map((p, i) => (
              <tr key={p.paper_id}><td>{i + 1}</td><td className="max-w-[460px]">{p.title}</td><td>{venueName(p)}</td><td>{p.year}</td><td>{p.our_institutions}</td><td>{fmt(p.citations)}</td><td>{doiLink(p.doi)}</td></tr>))}
            </tbody>
          </table>
        </div>
      </Section>

      <DataTable title={`All papers (${fmt(pap.length)})`} data={pap} columns={cols} filename="group9_papers_filtered.csv" />
      <p className="text-[12px] muted">Institutes: {INSTS.join(", ")}. A paper co-authored by faculty of both institutes appears once with both listed.</p>
    </div>
  );
}
