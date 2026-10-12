import { createContext, useCallback, useContext, useMemo, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { faculty, facultyById, papers, preprints, YEAR_MAX, YEAR_MIN, type Faculty, type Paper } from "./data";

export interface Filters {
  inst: "both" | "IIIT-H" | "IIIT-D";
  unit: string; // "" = all
  y0: number;
  y1: number;
  types: { journal: boolean; conference: boolean; preprint: boolean };
  desig: string; // "" = all
  q: string; // faculty search
}

const DEFAULTS: Filters = {
  inst: "both", unit: "", y0: YEAR_MIN, y1: YEAR_MAX,
  types: { journal: true, conference: true, preprint: false }, desig: "", q: "",
};

function parse(sp: URLSearchParams): Filters {
  const t = sp.get("types");
  const set = t ? new Set(t.split(",")) : null;
  return {
    inst: (sp.get("inst") as Filters["inst"]) || DEFAULTS.inst,
    unit: sp.get("unit") || "",
    y0: Number(sp.get("y0")) || DEFAULTS.y0,
    y1: Number(sp.get("y1")) || DEFAULTS.y1,
    types: set ? { journal: set.has("journal"), conference: set.has("conference"), preprint: set.has("preprint") } : DEFAULTS.types,
    desig: sp.get("desig") || "",
    q: sp.get("q") || "",
  };
}

function serialise(f: Filters): Record<string, string> {
  const o: Record<string, string> = {};
  if (f.inst !== DEFAULTS.inst) o.inst = f.inst;
  if (f.unit) o.unit = f.unit;
  if (f.y0 !== DEFAULTS.y0) o.y0 = String(f.y0);
  if (f.y1 !== DEFAULTS.y1) o.y1 = String(f.y1);
  const t = Object.entries(f.types).filter(([, v]) => v).map(([k]) => k).join(",");
  if (t !== "journal,conference") o.types = t;
  if (f.desig) o.desig = f.desig;
  if (f.q) o.q = f.q;
  return o;
}

interface Ctx {
  f: Filters;
  set: (patch: Partial<Filters>) => void;
  reset: () => void;
  fac: Faculty[];      // faculty passing inst/unit/desig/search
  pap: Paper[];        // papers passing inst/unit/year/type (+ faculty search, if any)
  facIds: Set<string>;
}
const FilterCtx = createContext<Ctx | null>(null);

export function FilterProvider({ children }: { children: ReactNode }) {
  const [sp, setSp] = useSearchParams();
  const f = useMemo(() => parse(sp), [sp]);
  const set = useCallback((patch: Partial<Filters>) => setSp(serialise({ ...f, ...patch }), { replace: true }), [f, setSp]);
  const reset = useCallback(() => setSp({}, { replace: true }), [setSp]);

  const fac = useMemo(() => {
    const q = f.q.trim().toLowerCase();
    return faculty.filter((x) =>
      (f.inst === "both" || x.institution === f.inst) &&
      (!f.unit || x.unit === f.unit || (x.units_secondary || "").split("; ").includes(f.unit)) &&
      (!f.desig || x.designation === f.desig) &&
      (!q || x.name.toLowerCase().includes(q)));
  }, [f]);
  const facIds = useMemo(() => new Set(fac.map((x) => x.faculty_id)), [fac]);
  const facetActive = !!(f.unit || f.desig || f.q);

  const pap = useMemo(() => {
    const pool = f.types.preprint ? papers.concat(preprints) : papers;
    return pool.filter((p) =>
      p.year >= f.y0 && p.year <= f.y1 &&
      (f.types as Record<string, boolean>)[p.type] &&
      (f.inst === "both" || p.our_institutions.split(";").includes(f.inst)) &&
      (!facetActive || (p.faculty || []).some((id) => facIds.has(id) && facultyById[id])));
  }, [f, facIds, facetActive]);

  return <FilterCtx.Provider value={{ f, set, reset, fac, pap, facIds }}>{children}</FilterCtx.Provider>;
}

export function useFilters(): Ctx {
  const c = useContext(FilterCtx);
  if (!c) throw new Error("useFilters outside provider");
  return c;
}
