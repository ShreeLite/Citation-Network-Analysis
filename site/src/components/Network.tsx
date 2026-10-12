import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { cssVar, useThemeVersion } from "./ui";

export interface NetNode { id: string; label: string; group: string; size: number; inst?: string; extra?: Record<string, unknown> }
export interface NetEdge { source: string; target: string; weight?: number }

/** Largest connected component size among nodes not in `removed`. */
function lcc(nodes: NetNode[], edges: NetEdge[], removed: Set<string>): number {
  const adj = new Map<string, string[]>();
  for (const n of nodes) if (!removed.has(n.id)) adj.set(n.id, []);
  for (const e of edges) {
    if (adj.has(e.source) && adj.has(e.target)) { adj.get(e.source)!.push(e.target); adj.get(e.target)!.push(e.source); }
  }
  const seen = new Set<string>();
  let best = 0;
  for (const s of adj.keys()) {
    if (seen.has(s)) continue;
    let size = 0;
    const stack = [s];
    seen.add(s);
    while (stack.length) {
      const v = stack.pop()!;
      size++;
      for (const w of adj.get(v)!) if (!seen.has(w)) { seen.add(w); stack.push(w); }
    }
    best = Math.max(best, size);
  }
  return best;
}

export function Network(props: {
  nodes: NetNode[]; edges: NetEdge[]; colorOf: (group: string) => string; directed?: boolean; height?: number;
  removable?: boolean; onSelect?: (id: string | null) => void; focus?: string; legend?: { label: string; color: string }[];
}) {
  const box = useRef<HTMLDivElement>(null);
  const cy = useRef<Core | null>(null);
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const [removeMode, setRemoveMode] = useState(false);
  const tv = useThemeVersion();
  const base = useMemo(() => lcc(props.nodes, props.edges, new Set()), [props.nodes, props.edges]);
  const now = useMemo(() => lcc(props.nodes, props.edges, removed), [props.nodes, props.edges, removed]);
  const modeRef = useRef(removeMode);
  modeRef.current = removeMode;

  useEffect(() => {
    if (!box.current) return;
    const maxSize = Math.max(1, ...props.nodes.map((n) => n.size));
    const els: ElementDefinition[] = [
      ...props.nodes.map((n) => ({ data: { id: n.id, label: n.label, group: n.group, w: 8 + 26 * Math.sqrt(n.size / maxSize) } })),
      ...props.edges.map((e, i) => ({ data: { id: `e${i}`, source: e.source, target: e.target, wt: e.weight ?? 1 } })),
    ];
    const ink = cssVar("--ink"), edge = cssVar("--axis"), surface = cssVar("--surface");
    const c = cytoscape({
      container: box.current, elements: els, wheelSensitivity: 0.25, minZoom: 0.15, maxZoom: 4,
      style: [
        { selector: "node", style: { width: "data(w)", height: "data(w)", "background-color": (el: any) => props.colorOf(el.data("group")), // eslint-disable-line @typescript-eslint/no-explicit-any
          "border-width": 2, "border-color": surface, label: "", "font-size": 10, color: ink, "text-valign": "bottom", "text-margin-y": 3 } },
        { selector: "edge", style: { width: (el: any) => Math.min(4, 0.6 + Math.sqrt(el.data("wt"))), "line-color": edge, opacity: 0.55, // eslint-disable-line @typescript-eslint/no-explicit-any
          "curve-style": props.directed ? "bezier" : "haystack", "target-arrow-shape": props.directed ? "triangle" : "none", "target-arrow-color": edge, "arrow-scale": 0.6 } },
        { selector: ".faded", style: { opacity: 0.12 } },
        { selector: ".hl", style: { label: "data(label)", "z-index": 10 } },
        { selector: "edge.hl", style: { "line-color": ink, opacity: 0.9 } },
        { selector: ".removed", style: { display: "none" } },
      ],
      layout: { name: "cose", animate: false, randomize: false, nodeRepulsion: () => 9000, idealEdgeLength: () => 60, numIter: 1500 } as any, // eslint-disable-line @typescript-eslint/no-explicit-any
    });
    c.on("mouseover", "node", (e) => {
      const n = e.target;
      c.elements().addClass("faded");
      n.closedNeighborhood().removeClass("faded").addClass("hl");
    });
    c.on("mouseout", "node", () => c.elements().removeClass("faded hl"));
    c.on("tap", "node", (e) => {
      const id = e.target.id();
      if (modeRef.current) {
        e.target.addClass("removed");
        setRemoved((s) => new Set(s).add(id));
      } else props.onSelect?.(id);
    });
    c.on("tap", (e) => { if (e.target === c) props.onSelect?.(null); });
    cy.current = c;
    setRemoved(new Set());
    return () => c.destroy();
  }, [props.nodes, props.edges, tv]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const c = cy.current;
    if (!c) return;
    c.nodes().style("background-color", (el: any) => props.colorOf(el.data("group"))); // eslint-disable-line @typescript-eslint/no-explicit-any
  }, [props.colorOf]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const c = cy.current;
    if (!c || !props.focus) return;
    const n = c.getElementById(props.focus);
    if (n.nonempty()) {
      c.animate({ center: { eles: n }, zoom: 1.6 }, { duration: 300 });
      c.elements().addClass("faded");
      n.closedNeighborhood().removeClass("faded").addClass("hl");
    }
  }, [props.focus]);

  const restore = () => { cy.current?.nodes().removeClass("removed"); setRemoved(new Set()); };
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2 text-[12px] ink-2 no-print">
        {props.legend?.map((l) => <span key={l.label} className="chip"><span className="dot" style={{ background: l.color }} />{l.label}</span>)}
        <span className="flex-1" />
        {props.removable && (
          <>
            <button className={`btn ${removeMode ? "btn-primary" : ""}`} onClick={() => setRemoveMode((m) => !m)} aria-pressed={removeMode}>
              {removeMode ? "Click-to-remove: on" : "Click-to-remove: off"}
            </button>
            <span className="chip tabnum" aria-live="polite">Largest component: {now} / {base}{removed.size ? ` (−${base - now} after removing ${removed.size})` : ""}</span>
            {removed.size > 0 && <button className="btn" onClick={restore}>Restore</button>}
          </>
        )}
        <button className="btn" onClick={() => cy.current?.fit(undefined, 20)}>Fit</button>
        <button className="btn" onClick={() => {
          const png = cy.current?.png({ full: true, scale: 3, bg: cssVar("--surface") });
          if (png) { const a = document.createElement("a"); a.href = png; a.download = "network.png"; a.click(); }
        }}>PNG</button>
      </div>
      <div ref={box} className="rounded-xl border hairline" style={{ height: props.height ?? 560, background: "var(--surface)" }} />
    </div>
  );
}
