import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { faculty, meta, YEAR_MAX, YEAR_MIN } from "./data";
import { FilterProvider, useFilters } from "./filters";
import Overview from "./tabs/Overview";

const Publications = lazy(() => import("./tabs/Publications"));
const FacultyTab = lazy(() => import("./tabs/Faculty"));
const Venues = lazy(() => import("./tabs/Venues"));
const Areas = lazy(() => import("./tabs/Areas"));
const CitationNet = lazy(() => import("./tabs/CitationNet"));
const CollabNet = lazy(() => import("./tabs/CollabNet"));
const Central = lazy(() => import("./tabs/Central"));
const Findings = lazy(() => import("./tabs/Findings"));
const Indian = lazy(() => import("./tabs/Indian"));
const IndianF2F = lazy(() => import("./tabs/IndianF2F"));
const Methods = lazy(() => import("./tabs/Methods"));

export const TABS = [
  { path: "overview", label: "Overview", el: <Overview /> },
  { path: "publications", label: "Publications", el: <Publications /> },
  { path: "faculty", label: "Faculty", el: <FacultyTab /> },
  { path: "venues", label: "Venues & Quality", el: <Venues /> },
  { path: "areas", label: "Research Areas", el: <Areas /> },
  { path: "citations", label: "Citation Network", el: <CitationNet /> },
  { path: "collaboration", label: "Collaboration Network", el: <CollabNet /> },
  { path: "central", label: "Centres vs Departments", el: <Central /> },
  { path: "findings", label: "Findings", el: <Findings /> },
  { path: "india", label: "Indian Connections", el: <Indian /> },
  { path: "india-f2f", label: "India Faculty↔Faculty", el: <IndianF2F /> },
  { path: "methods", label: "Data & Methods", el: <Methods /> },
];

function ThemeToggle() {
  const [theme, setTheme] = useState<string>(() => { try { return localStorage.getItem("theme") || ""; } catch { return ""; } });
  useEffect(() => {
    if (theme) document.documentElement.setAttribute("data-theme", theme);
    else document.documentElement.removeAttribute("data-theme");
    try { if (theme) localStorage.setItem("theme", theme); else localStorage.removeItem("theme"); } catch { /* storage unavailable */ }
  }, [theme]);
  const next = theme === "" ? "dark" : theme === "dark" ? "light" : "";
  return <button className="btn" onClick={() => setTheme(next)} title="Theme: system → dark → light">{theme === "" ? "Auto" : theme === "dark" ? "Dark" : "Light"}</button>;
}

function FilterBar() {
  const { f, set, reset } = useFilters();
  const units = useMemo(() => {
    const pool = faculty.filter((x) => f.inst === "both" || x.institution === f.inst);
    return [...new Set(pool.map((x) => x.unit))].filter(Boolean).sort();
  }, [f.inst]);
  const desigs = useMemo(() => [...new Set(faculty.map((x) => x.designation))].filter(Boolean).sort(), []);
  const years = Array.from({ length: YEAR_MAX - YEAR_MIN + 1 }, (_, i) => YEAR_MIN + i);
  return (
    <div className="card p-3 flex flex-wrap items-center gap-2 text-[13px] no-print" role="region" aria-label="Global filters">
      <label className="flex items-center gap-1.5">Institute
        <select value={f.inst} onChange={(e) => set({ inst: e.target.value as typeof f.inst, unit: "" })}>
          <option value="both">Both</option><option value="IIIT-H">IIIT-H</option><option value="IIIT-D">IIIT-D</option>
        </select></label>
      <label className="flex items-center gap-1.5">{f.inst === "IIIT-H" ? "Centre" : f.inst === "IIIT-D" ? "Department" : "Unit"}
        <select value={f.unit} onChange={(e) => set({ unit: e.target.value })}>
          <option value="">All</option>{units.map((u) => <option key={u}>{u}</option>)}
        </select></label>
      <label className="flex items-center gap-1.5">Years
        <select value={f.y0} onChange={(e) => set({ y0: Math.min(Number(e.target.value), f.y1) })}>{years.map((y) => <option key={y}>{y}</option>)}</select>
        –
        <select value={f.y1} onChange={(e) => set({ y1: Math.max(Number(e.target.value), f.y0) })}>{years.map((y) => <option key={y} value={y}>{y}{y === meta.partial_year ? " (partial)" : ""}</option>)}</select>
      </label>
      <fieldset className="flex items-center gap-2"><legend className="sr-only">Paper type</legend>
        {(["journal", "conference", "preprint"] as const).map((t) => (
          <label key={t} className="flex items-center gap-1 capitalize">
            <input type="checkbox" checked={f.types[t]} onChange={(e) => set({ types: { ...f.types, [t]: e.target.checked } })} />{t === "preprint" ? "incl. preprints" : t}
          </label>))}
      </fieldset>
      <label className="flex items-center gap-1.5">Designation
        <select value={f.desig} onChange={(e) => set({ desig: e.target.value })}>
          <option value="">All core</option>{desigs.map((d) => <option key={d}>{d}</option>)}
        </select></label>
      <input type="search" placeholder="Search faculty…" value={f.q} onChange={(e) => set({ q: e.target.value })} aria-label="Search faculty" className="min-w-[160px] flex-1 sm:flex-none" />
      <button className="btn" onClick={reset}>Reset</button>
    </div>
  );
}

function Shell() {
  const loc = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [loc.pathname]);
  return (
    <div className="min-h-screen">
      <header className="border-b hairline" style={{ background: "var(--surface)" }}>
        <div className="max-w-[1320px] mx-auto px-4 sm:px-6 py-4 flex flex-wrap items-center gap-3 justify-between">
          <div className="min-w-0">
            <div className="text-[12px] uppercase tracking-[0.12em] muted">DPCN · Group 9 · Research mapping 2016–2026</div>
            <h1 className="text-[22px] sm:text-[26px] font-semibold tracking-tight">IIIT Hyderabad <span className="muted font-normal">×</span> IIIT Delhi</h1>
          </div>
          <div className="flex gap-2 no-print">
            <a className="btn btn-primary" href="./group9_deliverables.zip" download>Download data</a>
            <ThemeToggle />
          </div>
        </div>
        <nav className="max-w-[1320px] mx-auto px-2 sm:px-4 overflow-x-auto no-print" aria-label="Sections">
          <ul className="flex gap-0.5 min-w-max xl:min-w-0 xl:flex-wrap">
            {TABS.map((t) => (
              <li key={t.path}>
                <NavLink to={{ pathname: `/${t.path}`, search: loc.search }} className={({ isActive }) =>
                  `block px-3 py-2.5 text-[13px] border-b-2 ${isActive ? "font-semibold" : "ink-2 border-transparent"}`}
                  style={({ isActive }) => (isActive ? { borderColor: "var(--accent)", color: "var(--ink)" } : {})}>{t.label}</NavLink>
              </li>))}
          </ul>
        </nav>
      </header>
      <main className="max-w-[1320px] mx-auto px-4 sm:px-6 py-5 flex flex-col gap-5">
        <FilterBar />
        <Suspense fallback={<div className="muted">Loading…</div>}>
          <Routes>
            {TABS.map((t) => <Route key={t.path} path={`/${t.path}`} element={t.el} />)}
            <Route path="*" element={<Navigate to="/overview" replace />} />
          </Routes>
        </Suspense>
      </main>
      <footer className="max-w-[1320px] mx-auto px-4 sm:px-6 py-8 text-[12px] muted">
        Data collected {meta.collection_date}. Sources: OpenAlex, DBLP, Crossref, Semantic Scholar, IIIT-H publications portal, institute websites, Scimago SJR, CORE. {meta.partial_year} is a partial year.
      </footer>
    </div>
  );
}

export default function App() {
  return <FilterProvider><Shell /></FilterProvider>;
}
