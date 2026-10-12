import { meta } from "../data";
import { fmt, pct, Section } from "../components/ui";

export default function Methods() {
  const qa = meta.qa || {};
  return (
    <div className="flex flex-col gap-6">
      <Section title="Downloads">
        <div className="card p-5 flex flex-col gap-2 text-[14px]">
          <a className="btn btn-primary w-fit" href="./group9_deliverables.zip" download>Download group9_deliverables.zip</a>
          <p className="ink-2">Contains the official files <code>group9_data.csv</code> (14 spec columns, one row per faculty author × paper), <code>citation_network.csv</code>, <code>authorship_network.csv</code>, <code>indian_connections.csv</code>, the formatted workbook <code>group9_full_dataset.xlsx</code> (README, papers, faculty, links, edges, findings, pre-joining papers, preprints, QA) and the QA report.</p>
        </div>
      </Section>
      <Section title="Coverage and quality checks">
        <div className="card p-5 overflow-x-auto">
          <table className="data tabnum"><tbody>
            {(meta.qa_rows || []).map((r: { metric: string; value: number | string }) => (
              <tr key={r.metric}><td>{r.metric.replace(/_/g, " ")}</td><td>{typeof r.value === "number" && r.value <= 1 && !/rows|faculty/.test(r.metric) ? pct(r.value) : fmt(r.value)}</td></tr>))}
          </tbody></table>
          {qa.note && <p className="text-[12px] muted mt-2">{qa.note}</p>}
        </div>
      </Section>
      <Section title="Sources">
        <ul className="card p-5 text-[14px] list-disc pl-9 flex flex-col gap-1">
          {(meta.sources || []).map((s: string) => <li key={s}>{s}</li>)}
        </ul>
      </Section>
      <Section title="Analytic choices">
        <ul className="card p-5 text-[14px] list-disc pl-9 flex flex-col gap-2">
          {(meta.choices || []).map((s: string) => <li key={s}>{s}</li>)}
        </ul>
      </Section>
      <Section title="Data dictionary (official file)">
        <div className="card p-5 overflow-x-auto"><table className="data"><thead><tr><th>Column</th><th>Meaning</th></tr></thead>
          <tbody>{(meta.dictionary || []).map((r: [string, string]) => <tr key={r[0]}><td><code>{r[0]}</code></td><td>{r[1]}</td></tr>)}</tbody></table></div>
      </Section>
      <Section title="Required panels → where they are">
        <div className="card p-5 overflow-x-auto"><table className="data"><thead><tr><th>Required panel</th><th>Tab</th></tr></thead>
          <tbody>{(meta.panels || []).map((r: [string, string]) => <tr key={r[0]}><td>{r[0]}</td><td>{r[1]}</td></tr>)}</tbody></table></div>
      </Section>
    </div>
  );
}
