import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { collaboration, coauthor, facultyById, YEAR_MIN, YEAR_MAX } from "../data";
import { useFilters } from "../filters";
import { cssVar, fmt, instColor, InstDot, Section } from "../components/ui";
import { Network, type NetEdge, type NetNode } from "../components/Network";

// fixed categorical order (validated reference palette); folded to "Other" past eight
const SLOTS_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
const SLOTS_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"];

export default function CollabNet() {
  const { f, facIds } = useFilters();
  const [colorBy, setColorBy] = useState<"unit" | "community" | "institution">("institution");
  const [focus, setFocus] = useState<string>("");
  const [sel, setSel] = useState<string | null>(null);
  const [animYear, setAnimYear] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopAnim = useCallback(() => { setPlaying(false); if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; } }, []);
  const startAnim = useCallback(() => {
    setAnimYear(YEAR_MIN);
    setPlaying(true);
  }, []);
  useEffect(() => {
    if (!playing) return;
    timerRef.current = setInterval(() => {
      setAnimYear((y) => { if (y === null || y >= YEAR_MAX) { stopAnim(); return null; } return y + 1; });
    }, 1200);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [playing, stopAnim]);

  const effectiveY1 = animYear ?? f.y1;
  const effectiveY0 = animYear !== null ? YEAR_MIN : f.y0;

  const g = useMemo(() => {
    const yrs = new Map<string, number[]>((coauthor.edge_years as [string, string, number[]][]).map(([a, b, y]) => [`${a}|${b}`, y]));
    const nodes: NetNode[] = (coauthor.nodes as { id: string; name: string; institution: string; unit: string; community: string; degree: number }[])
      .filter((n) => facIds.has(n.id))
      .map((n) => ({ id: n.id, label: n.name, group: colorBy === "institution" ? n.institution : colorBy === "unit" ? `${n.institution}:${n.unit}` : n.community, size: n.degree + 1, inst: n.institution }));
    const ids = new Set(nodes.map((n) => n.id));
    const edges: NetEdge[] = (coauthor.edges as { source: string; target: string; weight: number }[])
      .filter((e) => ids.has(e.source) && ids.has(e.target))
      .filter((e) => { const y = yrs.get(`${e.source}|${e.target}`) || yrs.get(`${e.target}|${e.source}`) || []; return y.some((v) => v >= effectiveY0 && v <= effectiveY1); })
      .map((e) => ({ source: e.source, target: e.target, weight: e.weight }));
    return { nodes, edges };
  }, [facIds, colorBy, effectiveY0, effectiveY1]);

  const groups = useMemo(() => {
    const c: Record<string, number> = {};
    for (const n of g.nodes) c[n.group] = (c[n.group] || 0) + 1;
    return Object.entries(c).sort((a, b) => b[1] - a[1]).map((x) => x[0]);
  }, [g.nodes]);
  const dark = cssVar("--surface").toLowerCase() === "#1a1a19";
  const colorOf = useMemo(() => (grp: string) => {
    if (colorBy === "institution") return instColor(grp);
    const i = groups.indexOf(grp);
    return i >= 0 && i < 8 ? (dark ? SLOTS_DARK : SLOTS_LIGHT)[i] : cssVar("--muted");
  }, [colorBy, groups, dark]);
  const legend = colorBy === "institution" ? [{ label: "IIIT-H", color: instColor("IIIT-H") }, { label: "IIIT-D", color: instColor("IIIT-D") }]
    : [...groups.slice(0, 8).map((g2) => ({ label: g2, color: colorOf(g2) })), ...(groups.length > 8 ? [{ label: `Other (${groups.length - 8} groups)`, color: cssVar("--muted") }] : [])];
  const person = sel ? facultyById[sel] : null;

  return (
    <div className="flex flex-col gap-5">
      <Section title="Faculty co-authorship network" intro="One node per core faculty member; an edge means at least one co-authored paper in the selected years. Node size = degree. Use click-to-remove to see how the largest connected group shrinks when a person leaves (Finding 1).">
        <div className="card p-4 flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2 text-[13px] no-print min-w-0">
            Colour by
            {(["institution", "unit", "community"] as const).map((c) => (
              <button key={c} className={`btn ${colorBy === c ? "btn-primary" : ""}`} onClick={() => setColorBy(c)}>{c === "unit" ? "official unit" : c === "community" ? "detected community" : "institute"}</button>))}
            <span className="flex-1" />
            <input type="search" list="fac-names" className="w-full sm:w-auto" placeholder="Focus on a person…" onChange={(e) => {
              const n = g.nodes.find((x) => x.label.toLowerCase() === e.target.value.toLowerCase()); if (n) setFocus(n.id); }} aria-label="Focus on a person" />
            <datalist id="fac-names">{g.nodes.map((n) => <option key={n.id} value={n.label} />)}</datalist>
          </div>
          <div className="flex items-center gap-2 text-[13px] no-print">
            <button className="btn" onClick={() => { if (playing) stopAnim(); else startAnim(); }}>{playing ? "Stop" : "Play timeline"}</button>
            {animYear !== null && <input type="range" min={YEAR_MIN} max={YEAR_MAX} value={animYear} onChange={(e) => { stopAnim(); setAnimYear(Number(e.target.value)); }} aria-label="Animation year" />}
            {animYear !== null && <span className="tabnum font-semibold">{animYear}</span>}
            {animYear !== null && <button className="btn" onClick={() => { stopAnim(); setAnimYear(null); }}>Reset</button>}
            {animYear !== null && <span className="muted">{g.edges.length} edges through {animYear}</span>}
          </div>
          <Network nodes={g.nodes} edges={g.edges} colorOf={colorOf} removable focus={focus} onSelect={setSel} legend={legend} height={620} />
          {person && (
            <div className="text-[13px] flex flex-wrap gap-4 items-center"><span className="flex items-center gap-2 font-semibold"><InstDot inst={person.institution} />{person.name}</span>
              <span className="ink-2">{person.unit} · degree {fmt(person.degree)} · betweenness {person.betweenness?.toFixed(3)} · community {person.community}</span></div>)}
        </div>
      </Section>
      <div className="grid lg:grid-cols-2 gap-4">
        <section className="card p-5 min-w-0">
          <h3 className="font-semibold text-[15px]">IIIT-H ↔ IIIT-D</h3>
          <p className="text-[13px] ink-2 mt-1">{fmt(collaboration.cross_institution_edges)} co-authored paper links between the two institutes, across {fmt(collaboration.cross_institution_pairs)} distinct faculty pairs.</p>
          <div className="overflow-x-auto"><table className="data tabnum mt-3"><thead><tr><th>Hub bridging the institutes</th><th>Unit</th><th>Cross-institute papers</th></tr></thead>
            <tbody>{(collaboration.hub_bridgers as { faculty_id: string; cross_institution_papers: number }[]).map((h) => (
              <tr key={h.faculty_id}><td className="flex items-center gap-2"><InstDot inst={facultyById[h.faculty_id]?.institution || ""} />{facultyById[h.faculty_id]?.name || h.faculty_id}</td><td>{facultyById[h.faculty_id]?.unit}</td><td>{h.cross_institution_papers}</td></tr>))}</tbody></table></div>
        </section>
        <section className="card p-5 min-w-0">
          <h3 className="font-semibold text-[15px]">Most central faculty</h3>
          <div className="overflow-x-auto"><table className="data tabnum mt-2"><thead><tr><th>Name</th><th>Degree</th><th>Betweenness</th></tr></thead>
            <tbody>{Object.values(facultyById).filter((x) => facIds.has(x.faculty_id)).sort((a, b) => (b.betweenness || 0) - (a.betweenness || 0)).slice(0, 10).map((x) => (
              <tr key={x.faculty_id}><td className="flex items-center gap-2"><InstDot inst={x.institution} />{x.name}</td><td>{fmt(x.degree)}</td><td>{(x.betweenness || 0).toFixed(3)}</td></tr>))}</tbody></table></div>
          <p className="text-[12px] muted mt-2">Betweenness: normalised, on the unweighted faculty graph of both institutes. Communities: Louvain (seed 42) within each institute.</p>
        </section>
      </div>
    </div>
  );
}
