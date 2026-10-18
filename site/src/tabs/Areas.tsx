import { useMemo, useState } from "react";
import { INSTS, required } from "../data";
import { useFilters } from "../filters";
import { ChartCard, cssVar, instColor } from "../components/ui";

function hexToRgb(hex: string): [number, number, number] {
  const m = hex.match(/^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
  return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [100, 100, 100];
}

function shade(rgb: [number, number, number], t: number): string {
  const mix = (c: number) => Math.round(255 - (255 - c) * (0.3 + 0.7 * t));
  return `rgb(${mix(rgb[0])}, ${mix(rgb[1])}, ${mix(rgb[2])})`;
}

export default function Areas() {
  const { f, pap } = useFilters();
  const insts = f.inst === "both" ? INSTS : [f.inst];
  const [inst, setInst] = useState<string>(insts[0]);
  const fields = useMemo(() => {
    const m: Record<string, Record<string, number>> = {};
    for (const p of pap) for (const i of p.our_institutions.split(";")) {
      if (!insts.includes(i as never)) continue;
      const k = p.field || "Unknown";
      m[k] = m[k] || {};
      m[k][i] = (m[k][i] || 0) + 1;
    }
    const tot = Object.fromEntries(insts.map((i) => [i, Object.values(m).reduce((s, r) => s + (r[i] || 0), 0)]));
    const rows = Object.entries(m).map(([k, r]) => ({ field: k, ...Object.fromEntries(insts.map((i) => [i, tot[i] ? (r[i] || 0) / tot[i] : 0])), n: Object.values(r).reduce((a, b) => a + b, 0) }))
      .sort((a, b) => b.n - a.n).slice(0, 12);
    return rows as ({ field: string; n: number } & Record<string, number>)[];
  }, [pap, insts.join()]); // eslint-disable-line react-hooks/exhaustive-deps

  const tree = useMemo(() => {
    const m: Record<string, Record<string, number>> = {};
    for (const p of pap) if (p.our_institutions.split(";").includes(inst)) {
      const fl = p.field || "Unknown", sf = p.subfield || "Unknown";
      m[fl] = m[fl] || {};
      m[fl][sf] = (m[fl][sf] || 0) + 1;
    }
    const entries = Object.entries(m).map(([fl, subs]) => {
      const total = Object.values(subs).reduce((a, b) => a + b, 0);
      return { name: fl, total, subs };
    }).sort((a, b) => b.total - a.total);
    const maxVal = entries[0]?.total || 1;
    const rgb = hexToRgb(instColor(inst));
    return entries.map((e) => {
      const fieldT = 0.3 + 0.7 * (e.total / maxVal);
      const fieldColor = shade(rgb, fieldT);
      const subEntries = Object.entries(e.subs).sort((a, b) => b[1] - a[1]);
      const subMax = subEntries[0]?.[1] || 1;
      return {
        name: e.name,
        itemStyle: { color: fieldColor },
        children: subEntries.map(([s, n]) => ({
          name: s, value: n,
          itemStyle: { color: shade(rgb, 0.2 + 0.6 * (n / subMax) * (e.total / maxVal)) },
        })),
      };
    });
  }, [pap, inst]);

  const unitMix = useMemo(() => {
    const rows = (required.unit_fields as { institution: string; unit: string; field: string; papers: number }[]).filter((r) => r.institution === inst);
    const units = [...new Set(rows.map((r) => r.unit))];
    const topFields = Object.entries(rows.reduce((m: Record<string, number>, r) => ({ ...m, [r.field]: (m[r.field] || 0) + r.papers }), {}))
      .sort((a, b) => b[1] - a[1]).slice(0, 6).map((x) => x[0]);
    const tot = Object.fromEntries(units.map((u) => [u, rows.filter((r) => r.unit === u).reduce((s, r) => s + r.papers, 0)]));
    return { units, topFields, share: (u: string, fl: string) => (tot[u] ? (rows.find((r) => r.unit === u && r.field === fl)?.papers || 0) / tot[u] : 0), tot };
  }, [inst]);

  return (
    <div className="flex flex-col gap-5">
      <ChartCard title="Research fields" caption="Share of each institute's papers by OpenAlex field (top 12 fields)." deps={[fields]} height={380}
        method="OpenAlex primary topic → subfield → field of each paper. Shares are within-institute, so the two institutes are comparable despite different sizes."
        option={() => ({ grid: { left: 8, right: 24 }, xAxis: { type: "value", axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
          yAxis: { type: "category", inverse: true, data: fields.map((r) => r.field), axisLabel: { width: 200, overflow: "truncate" } },
          tooltip: { trigger: "axis", valueFormatter: (v: number) => `${(v * 100).toFixed(1)}%` },
          series: insts.map((i) => ({ name: i, type: "bar", data: fields.map((r) => r[i]), itemStyle: { color: instColor(i), borderRadius: [0, 4, 4, 0] }, barMaxWidth: 12 })) })}
        table={() => ({ columns: ["field", ...insts.map((i) => `${i} share`), "papers"], rows: fields.map((r) => [r.field, ...insts.map((i) => `${(r[i] * 100).toFixed(1)}%`), r.n]) })} />

      <div className="flex items-center gap-2 text-[13px] no-print">Institute for the breakdowns below:
        {insts.map((i) => <button key={i} className={`btn ${inst === i ? "btn-primary" : ""}`} onClick={() => setInst(i)}>{i}</button>)}</div>

      <ChartCard title={`${inst}: fields and subfields`} caption="Treemap of papers by field (outer) and subfield (inner); area = papers." deps={[tree]} height={460}
        method="Same OpenAlex classification as above; papers counted once per institute."
        option={() => ({ legend: { show: false }, tooltip: { trigger: "item" },
          series: [{ type: "treemap", data: tree, roam: false, nodeClick: "zoomToNode", breadcrumb: { show: true, bottom: 0 },
            label: { show: true, color: cssVar("--surface") }, upperLabel: { show: true, height: 22, color: cssVar("--surface") },
            levels: [{ itemStyle: { borderColor: cssVar("--surface"), borderWidth: 2, gapWidth: 2 } },
                     { itemStyle: { borderColor: cssVar("--surface"), borderWidth: 1, gapWidth: 1 } }] }] })}
        table={() => ({ columns: ["field", "subfield", "papers"], rows: tree.flatMap((t) => t.children.map((c) => [t.name, c.name, c.value])) })} />

      <ChartCard title={`${inst}: topic mix per ${inst === "IIIT-H" ? "centre" : "department"}`} caption="Share of each unit's papers in the institute's six largest fields (a paper counts once per unit)." deps={[unitMix]} height={Math.max(260, 40 * unitMix.units.length)}
        method="Unit = the faculty member's primary centre/department from the official website. Darker = larger share. Unit sizes in the table."
        option={() => ({ legend: { show: false }, grid: { left: 8, right: 70, top: 10, bottom: 60 },
          tooltip: { trigger: "item", formatter: (p: any) => `${unitMix.units[p.value[1]]} · ${unitMix.topFields[p.value[0]]}: ${(p.value[2] * 100).toFixed(1)}%` }, // eslint-disable-line @typescript-eslint/no-explicit-any
          xAxis: { type: "category", data: unitMix.topFields, axisLabel: { interval: 0, rotate: 20, width: 120, overflow: "truncate" } },
          yAxis: { type: "category", data: unitMix.units },
          visualMap: { min: 0, max: 1, calculable: false, orient: "vertical", right: 0, top: "middle", inRange: { color: inst === "IIIT-D" ? ["#fde4d6", "#eb6834", "#8a3510"] : ["#d6e8fb", "#2a78d6", "#0d366b"] }, formatter: (v: number) => `${Math.round(v * 100)}%`, textStyle: { color: cssVar("--muted") } },
          series: [{ type: "heatmap", data: unitMix.units.flatMap((u, y) => unitMix.topFields.map((fl, x) => [x, y, unitMix.share(u, fl)])), itemStyle: { borderColor: cssVar("--surface"), borderWidth: 2 } }] })}
        table={() => ({ columns: ["unit", "papers", ...unitMix.topFields], rows: unitMix.units.map((u) => [u, unitMix.tot[u], ...unitMix.topFields.map((fl) => `${(unitMix.share(u, fl) * 100).toFixed(1)}%`)]) })} />
    </div>
  );
}
