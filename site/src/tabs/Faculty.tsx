import { useMemo, useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { coauthor, facultyById, type Faculty } from "../data";
import { useFilters } from "../filters";
import { ChartCard, DataTable, fmt, instColor, InstDot } from "../components/ui";

const ch = createColumnHelper<Faculty>();

function Drawer({ f, onClose }: { f: Faculty; onClose: () => void }) {
  const co = useMemo(() => {
    const out: { id: string; papers: number }[] = [];
    for (const e of coauthor.edges as { source: string; target: string; papers: number }[]) {
      if (e.source === f.faculty_id) out.push({ id: e.target, papers: e.papers });
      else if (e.target === f.faculty_id) out.push({ id: e.source, papers: e.papers });
    }
    return out.sort((a, b) => b.papers - a.papers);
  }, [f]);
  const years = Object.keys(f.per_year || {}).map(Number).sort();
  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label={`Profile of ${f.name}`}>
      <div className="absolute inset-0" style={{ background: "rgba(0,0,0,0.35)" }} onClick={onClose} />
      <aside className="relative w-full max-w-[560px] h-full overflow-y-auto p-6 flex flex-col gap-4" style={{ background: "var(--page)" }}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-[12px] muted"><InstDot inst={f.institution} />{f.institution} · {f.unit}{f.units_secondary ? ` (+ ${f.units_secondary})` : ""}</div>
            <h3 className="text-[22px] font-semibold">{f.name}</h3>
            <div className="ink-2 text-[13px]">{f.designation}{f.joining_year ? ` · joined ${f.joining_year}` : ""}{f.status === "former" ? " · former" : ""}</div>
          </div>
          <button className="btn" onClick={onClose} autoFocus>Close</button>
        </div>
        <div className="grid grid-cols-3 gap-2 text-[13px]">
          {[["Papers", f.papers], ["Citations", f.citations], ["h (dataset)", f.h_index_dataset], ["h (lifetime)", f.h_index_lifetime], ["Degree", f.degree], ["Betweenness", f.betweenness?.toFixed(3)]].map(([k, v]) => (
            <div key={k as string} className="card p-3"><div className="muted text-[11px] uppercase">{k}</div><div className="text-[18px] font-semibold">{fmt(v)}</div></div>))}
        </div>
        <ChartCard title="Papers per year" caption="Main-set papers by publication year." method="Within tenure or institute-affiliated papers only." height={200} deps={[f]}
          option={() => ({ legend: { show: false }, xAxis: { type: "category", data: years.map(String) }, yAxis: { type: "value" },
            series: [{ type: "bar", data: years.map((y) => f.per_year[y]), itemStyle: { color: instColor(f.institution), borderRadius: [4, 4, 0, 0] }, barMaxWidth: 18 }] })}
          table={() => ({ columns: ["year", "papers"], rows: years.map((y) => [y, f.per_year[y]]) })} />
        <div className="card p-4"><h4 className="font-semibold text-[14px] mb-2">Top venues</h4>
          <ul className="text-[13px] flex flex-col gap-1">{Object.entries(f.venues || {}).map(([v, n]) => <li key={v} className="flex justify-between gap-3"><span>{v}</span><span className="tabnum muted">{n}</span></li>)}</ul></div>
        <div className="card p-4"><h4 className="font-semibold text-[14px] mb-2">Research fields</h4>
          <ul className="text-[13px] flex flex-col gap-1">{Object.entries(f.fields || {}).map(([v, n]) => <li key={v} className="flex justify-between gap-3"><span>{v}</span><span className="tabnum muted">{n}</span></li>)}</ul></div>
        <div className="card p-4"><h4 className="font-semibold text-[14px] mb-2">Faculty co-authors ({co.length})</h4>
          <ul className="text-[13px] flex flex-col gap-1">{co.slice(0, 25).map((c) => <li key={c.id} className="flex justify-between gap-3"><span className="flex items-center gap-2"><InstDot inst={facultyById[c.id]?.institution || ""} />{facultyById[c.id]?.name || c.id}</span><span className="tabnum muted">{c.papers} papers</span></li>)}</ul>
          {co.length === 0 && <p className="text-[13px] muted">No co-authored papers with other core faculty in the main set.</p>}
          <p className="text-[12px] muted mt-2">Network position: community {f.community || "—"}; internal degree {fmt(f.degree_internal)}; internal betweenness {f.betweenness_internal?.toFixed(3) ?? "—"}.</p>
        </div>
      </aside>
    </div>
  );
}

export default function FacultyTab() {
  const { fac } = useFilters();
  const [sel, setSel] = useState<Faculty | null>(null);
  const cols = useMemo(() => [
    ch.accessor("name", { header: "Name", cell: (c) => <button className="link text-left" onClick={() => setSel(c.row.original)}>{c.getValue()}</button> }),
    ch.accessor("institution", { header: "Inst." }),
    ch.accessor("unit", { header: "Unit" }),
    ch.accessor("designation", { header: "Designation" }),
    ch.accessor("papers", { header: "Papers" }),
    ch.accessor("citations", { header: "Citations", cell: (c) => fmt(c.getValue()) }),
    ch.accessor("h_index_dataset", { header: "h (2016–26)" }),
    ch.accessor("h_index_lifetime", { header: "h (lifetime)", cell: (c) => fmt(c.getValue()) }),
    ch.accessor("top_venue", { header: "Top venue" }),
    ch.accessor("degree", { header: "Degree", cell: (c) => fmt(c.getValue()) }),
    ch.accessor("betweenness", { header: "Betweenness", cell: (c) => (c.getValue() ?? 0).toFixed(3) }),
  ], []);
  const hist = useMemo(() => {
    const max = Math.max(0, ...fac.map((x) => x.h_index_dataset));
    const bins = Array.from({ length: Math.ceil((max + 1) / 2) }, (_, i) => i * 2);
    const by = (inst: string) => bins.map((b) => fac.filter((x) => x.institution === inst && x.h_index_dataset >= b && x.h_index_dataset < b + 2).length);
    return { bins, h: by("IIIT-H"), d: by("IIIT-D") };
  }, [fac]);
  return (
    <div className="flex flex-col gap-5">
      <ChartCard title="h-index distribution" caption="Faculty per h-index band (2016–2026 dataset h-index)." deps={[hist]}
        method="Dataset h-index: largest h such that h of the person's main-set papers have ≥ h OpenAlex citations. Lifetime h-index (OpenAlex summary_stats, max over the person's author IDs) is in the table."
        option={() => ({ xAxis: { type: "category", data: hist.bins.map((b) => `${b}–${b + 1}`), name: "h-index" }, yAxis: { type: "value", name: "faculty" },
          series: [{ name: "IIIT-H", type: "bar", data: hist.h, itemStyle: { color: instColor("IIIT-H"), borderRadius: [4, 4, 0, 0] } },
                   { name: "IIIT-D", type: "bar", data: hist.d, itemStyle: { color: instColor("IIIT-D"), borderRadius: [4, 4, 0, 0] } }] })}
        table={() => ({ columns: ["h band", "IIIT-H", "IIIT-D"], rows: hist.bins.map((b, i) => [`${b}–${b + 1}`, hist.h[i], hist.d[i]]) })} />
      <DataTable title={`Faculty performance (${fac.length})`} data={fac} columns={cols} filename="group9_faculty_filtered.csv" pageSize={30} />
      <p className="text-[12px] muted">Click a name for the profile drawer. Degree and betweenness are on the faculty-only co-authorship network (both institutes).</p>
      {sel && <Drawer f={sel} onClose={() => setSel(null)} />}
    </div>
  );
}
