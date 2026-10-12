import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import * as echarts from "echarts";
import {
  flexRender, getCoreRowModel, getFilteredRowModel, getPaginationRowModel, getSortedRowModel, useReactTable,
  type ColumnDef, type SortingState,
} from "@tanstack/react-table";

/* ---------- theme helpers ---------- */
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
export const instColor = (i: string) => cssVar(i === "IIIT-D" ? "--iiitd" : "--iiith");
export const typeColor = (t: string) => cssVar(t === "journal" ? "--journal" : t === "conference" ? "--conference" : "--preprint");

export function useThemeVersion(): number {
  const [v, setV] = useState(0);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const bump = () => setV((x) => x + 1);
    mq.addEventListener("change", bump);
    const obs = new MutationObserver(bump);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => { mq.removeEventListener("change", bump); obs.disconnect(); };
  }, []);
  return v;
}

export function baseOption(): echarts.EChartsCoreOption {
  const ink2 = cssVar("--ink-2"), muted = cssVar("--muted"), grid = cssVar("--grid"), axis = cssVar("--axis");
  return {
    textStyle: { fontFamily: "Inter Variable, system-ui, sans-serif", color: ink2 },
    grid: { left: 48, right: 20, top: 36, bottom: 36, containLabel: true },
    tooltip: { trigger: "axis", backgroundColor: cssVar("--surface"), borderColor: cssVar("--border"), textStyle: { color: cssVar("--ink"), fontSize: 12 } },
    legend: { top: 0, right: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: ink2, fontSize: 12 } },
    xAxis: { axisLine: { lineStyle: { color: axis } }, axisTick: { show: false }, axisLabel: { color: muted }, splitLine: { show: false } },
    yAxis: { axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: muted }, splitLine: { lineStyle: { color: grid, width: 1 } } },
  };
}

function merge(a: any, b: any): any { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (Array.isArray(b) || typeof b !== "object" || b === null) return b;
  const o = { ...(a || {}) };
  for (const k of Object.keys(b)) o[k] = k in o && typeof o[k] === "object" && !Array.isArray(o[k]) ? merge(o[k], b[k]) : b[k];
  return o;
}

/* ---------- Chart panel ---------- */
export interface TableView { columns: string[]; rows: (string | number | null | undefined)[][] }

export function ChartCard(props: {
  title: string; caption: string; method: string; option: () => echarts.EChartsCoreOption; height?: number;
  table?: () => TableView; actions?: ReactNode; deps?: unknown[]; onClick?: (p: any) => void; // eslint-disable-line @typescript-eslint/no-explicit-any
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const [showTable, setShowTable] = useState(false);
  const tv = useThemeVersion();
  useEffect(() => {
    if (!ref.current || showTable) return;
    chart.current = echarts.init(ref.current, undefined, { renderer: "canvas" });
    const ro = new ResizeObserver(() => chart.current?.resize());
    ro.observe(ref.current);
    return () => { ro.disconnect(); chart.current?.dispose(); chart.current = null; };
  }, [showTable]);
  useEffect(() => {
    if (!chart.current) return;
    chart.current.setOption(merge(baseOption(), props.option()), true);
    chart.current.off("click");
    if (props.onClick) chart.current.on("click", props.onClick);
  }, [tv, showTable, ...(props.deps || [])]); // eslint-disable-line react-hooks/exhaustive-deps

  const png = () => {
    if (!chart.current) return;
    const url = chart.current.getDataURL({ type: "png", pixelRatio: 3, backgroundColor: cssVar("--surface") });
    download(url, `${slug(props.title)}.png`);
  };
  const csv = () => { if (props.table) downloadCsv(props.table(), `${slug(props.title)}.csv`); };
  return (
    <section className="card p-4 sm:p-5 flex flex-col gap-2 min-w-0">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold leading-snug">{props.title}</h3>
          <p className="text-[13px] ink-2 mt-0.5">{props.caption} <MethodTip text={props.method} /></p>
        </div>
        <div className="flex gap-1.5 shrink-0 no-print">
          {props.actions}
          {props.table && <button className="btn" onClick={() => setShowTable((s) => !s)} aria-pressed={showTable}>{showTable ? "Chart" : "Table"}</button>}
          {!showTable && <button className="btn" onClick={png} title="Download PNG">PNG</button>}
          {props.table && <button className="btn" onClick={csv} title="Download CSV">CSV</button>}
        </div>
      </header>
      {showTable && props.table ? <MiniTable view={props.table()} /> : <div ref={ref} style={{ height: props.height ?? 320, width: "100%" }} />}
    </section>
  );
}

export function MethodTip({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-block align-baseline">
      <button className="tooltip-trigger text-[12px] muted" onClick={() => setOpen((o) => !o)} onBlur={() => setOpen(false)} aria-expanded={open}>method</button>
      {open && <span role="tooltip" className="card absolute z-30 left-0 top-6 w-72 p-3 text-[12px] ink-2 shadow-lg">{text}</span>}
    </span>
  );
}

function MiniTable({ view }: { view: TableView }) {
  return (
    <div className="overflow-auto max-h-[420px]">
      <table className="data tabnum">
        <thead><tr>{view.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{view.rows.map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j}>{fmt(v)}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

/* ---------- Data table ---------- */
export function DataTable<T extends object>({ data, columns, title, filename, pageSize = 25, search = true }: {
  data: T[]; columns: ColumnDef<T, any>[]; title?: string; filename: string; pageSize?: number; search?: boolean; // eslint-disable-line @typescript-eslint/no-explicit-any
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const table = useReactTable({
    data, columns, state: { sorting, globalFilter }, onSortingChange: setSorting, onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(), initialState: { pagination: { pageSize } },
  });
  const exportCsv = () => {
    const rows = table.getFilteredRowModel().rows;
    const cols = table.getAllLeafColumns();
    downloadCsv({ columns: cols.map((c) => String(c.columnDef.header ?? c.id)), rows: rows.map((r) => cols.map((c) => r.getValue(c.id) as string)) }, filename);
  };
  const n = table.getFilteredRowModel().rows.length;
  return (
    <section className="card p-4 sm:p-5 min-w-0">
      <header className="flex flex-wrap items-center justify-between gap-2 mb-3">
        {title && <h3 className="text-[15px] font-semibold">{title}</h3>}
        <div className="flex gap-2 items-center no-print">
          {search && <input type="search" placeholder="Search table…" value={globalFilter} onChange={(e) => setGlobalFilter(e.target.value)} />}
          <button className="btn" onClick={exportCsv}>CSV</button>
        </div>
      </header>
      <div className="overflow-x-auto">
        <table className="data tabnum">
          <thead>{table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>{hg.headers.map((h) => (
              <th key={h.id} onClick={h.column.getToggleSortingHandler()} aria-sort={h.column.getIsSorted() === "asc" ? "ascending" : h.column.getIsSorted() === "desc" ? "descending" : "none"}>
                {flexRender(h.column.columnDef.header, h.getContext())}{{ asc: " ↑", desc: " ↓" }[h.column.getIsSorted() as string] ?? ""}
              </th>))}</tr>))}
          </thead>
          <tbody>{table.getRowModel().rows.map((r) => (
            <tr key={r.id}>{r.getVisibleCells().map((c) => <td key={c.id}>{flexRender(c.column.columnDef.cell, c.getContext())}</td>)}</tr>))}
          </tbody>
        </table>
      </div>
      <footer className="flex items-center justify-between mt-3 text-[12px] muted no-print">
        <span>{n.toLocaleString()} rows</span>
        <span className="flex gap-2 items-center">
          <button className="btn" disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()}>Prev</button>
          <span>Page {table.getState().pagination.pageIndex + 1} of {Math.max(1, table.getPageCount())}</span>
          <button className="btn" disabled={!table.getCanNextPage()} onClick={() => table.nextPage()}>Next</button>
        </span>
      </footer>
    </section>
  );
}

/* ---------- KPI ---------- */
export function Kpi({ label, value, sub, help }: { label: string; value: ReactNode; sub?: ReactNode; help?: string }) {
  return (
    <div className="card p-4 min-w-0" title={help}>
      <div className="text-[12px] uppercase tracking-wide muted">{label}</div>
      <div className="text-[28px] font-semibold leading-tight mt-1">{value}</div>
      {sub && <div className="text-[12px] ink-2 mt-1">{sub}</div>}
    </div>
  );
}

export function InstDot({ inst }: { inst: string }) {
  return <span className="dot" style={{ background: inst === "IIIT-D" ? "var(--iiitd)" : "var(--iiith)" }} />;
}

export function Section({ title, intro, children }: { title: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <div><h2 className="text-[20px] font-semibold tracking-tight">{title}</h2>{intro && <p className="ink-2 text-[14px] mt-1 max-w-3xl">{intro}</p>}</div>
      {children}
    </section>
  );
}

export function PartialNote() {
  return <span className="chip" title="2026 contains papers indexed up to the collection date only">2026 = partial year</span>;
}

/* ---------- utils ---------- */
export function fmt(v: unknown, digits = 2): string {
  if (v === null || v === undefined || (typeof v === "number" && Number.isNaN(v))) return "—";
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toLocaleString(undefined, { maximumFractionDigits: digits });
  if (typeof v === "boolean") return v ? "Yes" : "No";
  return String(v);
}
export const pct = (v: number | null | undefined, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(d)}%`);
export function slug(s: string) { return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
export function download(href: string, name: string) { const a = document.createElement("a"); a.href = href; a.download = name; a.click(); }
export function downloadCsv(view: TableView, name: string) {
  const esc = (v: unknown) => { const s = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const text = [view.columns.map(esc).join(","), ...view.rows.map((r) => r.map(esc).join(","))].join("\n");
  download(URL.createObjectURL(new Blob([text], { type: "text/csv" })), name);
}
export function useMemoOnce<T>(f: () => T): T { return useMemo(f, []); } // eslint-disable-line react-hooks/exhaustive-deps
