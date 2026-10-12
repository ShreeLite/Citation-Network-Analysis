/* eslint-disable @typescript-eslint/no-explicit-any */
import { pct } from "../components/ui";

export interface Headline {
  id: string; n: number; kicker: string; question: string; number: string; numberLabel: string;
  recommendation: string; audience: string;
}

const INST = ["IIIT-H", "IIIT-D"];

export function headlines(F: any): Headline[] {
  const out: Headline[] = [];
  // 1 hidden glue
  {
    const nf = F.f1?.n_flagged || {};
    const hp = F.f1?.headline_person;
    const total = INST.reduce((s, i) => s + (nf[i] || 0), 0);
    out.push({
      id: "f1", n: 1, kicker: "1 · The hidden glue", question: "Who holds the collaboration network together without being among its most connected people?",
      number: String(total), numberLabel: hp ? `faculty with top-15% betweenness but below-median degree; removing ${hp.name} cuts the largest connected group by ${hp.lcc_drop} people (${pct(hp.lcc_drop_pct, 0)}).` : "faculty flagged as bridges with ordinary degree",
      recommendation: "Recognise and protect bridging roles in promotion and retention reviews — losing one of these people fragments collaboration more than losing a prolific author.",
      audience: "Institute leadership (Director, Dean of Faculty)",
    });
  }
  // 2 weak points
  {
    const pu = F.f2?.per_unit || [];
    const aps = pu.reduce((s: number, r: any) => s + r.articulation_points, 0);
    const worst = [...pu].sort((a: any, b: any) => b.articulation_points - a.articulation_points)[0];
    out.push({
      id: "f2", n: 2, kicker: "2 · Weak points in each unit", question: "Which units' internal collaboration hangs on single people?",
      number: String(aps), numberLabel: worst ? `single points of failure across all units; most in ${worst.unit} (${worst.institution}, ${worst.articulation_points} of ${worst.n_faculty} faculty).` : "articulation points",
      recommendation: "Plan succession for these people: add co-supervision and pair them with a second faculty member in each sub-area; use the list to decide where to hire next.",
      audience: "Centre heads (IIIT-H) and department heads (IIIT-D)",
    });
  }
  // 3 integration
  {
    const s = (F.f3?.summary || []).filter((r: any) => r.unit === "All units");
    const txt = s.map((r: any) => `${r.institution}: ${pct(r.share_zero_after_3y, 0)} of ${r.n}`).join(" · ");
    const worst = [...s].sort((a: any, b: any) => b.share_zero_after_3y - a.share_zero_after_3y)[0];
    out.push({
      id: "f3", n: 3, kicker: "3 · How long new faculty take to fit in", question: "After three years, how many new faculty still have no co-author inside their institute?",
      number: worst ? pct(worst.share_zero_after_3y, 0) : "—", numberLabel: `of faculty who joined 2016+ still had zero internal co-authors after 3 years (${txt}).`,
      recommendation: "Pair each new hire with an established colleague through a mentoring scheme and a joint seed grant in year one.",
      audience: "Deans (Faculty Affairs / Research)",
    });
  }
  // 4 missed collaborations
  {
    const c = F.f4?.counts || {};
    const cross = c["cross-institute"] || 0;
    const total = Object.values(c).reduce((s: number, v: any) => s + v, 0) as number;
    out.push({
      id: "f4", n: 4, kicker: "4 · Collaborations waiting to happen", question: "Which pairs work on the same topics but have never written together or shared a co-author?",
      number: String(total), numberLabel: `high-overlap pairs (topic Jaccard ≥ ${F.f4?.threshold}) with no joint paper and no shared co-author; ${cross} span IIIT-H ↔ IIIT-D.`,
      recommendation: "Use the list as a matchmaking shortlist for seed grants, joint workshops and an IIIT-H–IIIT-D faculty exchange.",
      audience: "Faculty and the research office",
    });
  }
  // 5 bridging pays?
  {
    const p = F.f5?.pooled_year_normalised || {};
    const cross = p["cross-unit"]?.median_norm_citations, within = p["within-unit"]?.median_norm_citations;
    const ratio = cross && within ? cross / within : null;
    const wins = F.f5?.years_cross_higher, of = F.f5?.years_compared;
    const pays = ratio !== null && ratio > 1.05;
    const hurts = ratio !== null && ratio < 0.95;
    out.push({
      id: "f5", n: 5, kicker: "5 · Does bridging pay off?", question: "Are papers that cross unit boundaries cited more than within-unit papers from the same year?",
      number: ratio === null ? "—" : `${ratio.toFixed(2)}×`, numberLabel: `year-normalised median citations, cross-unit vs within-unit (cross-unit higher in ${wins} of ${of} full years; n = ${p["cross-unit"]?.n ?? 0} vs ${p["within-unit"]?.n ?? 0}).`,
      recommendation: pays ? "Fund interdisciplinary work: cross-unit papers earn more citations than same-year within-unit papers." :
        hurts ? "Do not assume interdisciplinary work pays in citations: cross-unit papers are cited less; fund it for other reasons and track outcomes." :
          "Citations are no reason for or against cross-unit funding: impact is similar; decide on strategic grounds.",
      audience: "Research office and funding committees",
    });
  }
  // 6 concentration
  {
    const rows = (F.f6?.rows || []).filter((r: any) => r.year === "all");
    const txt = rows.map((r: any) => `${r.institution}: ${pct(r.top10_share_citations, 0)}`).join(" · ");
    const top = [...rows].sort((a: any, b: any) => b.top10_share_citations - a.top10_share_citations)[0];
    out.push({
      id: "f6", n: 6, kicker: "6 · Concentration risk", question: "How much of each institute's output rests on its top 10% of faculty?",
      number: top ? pct(top.top10_share_citations, 0) : "—", numberLabel: `of citations held by the top 10% of faculty (${txt}).`,
      recommendation: "Support mid-career faculty (teaching relief, students, seed funds) so output does not depend on a few people.",
      audience: "Institute leadership",
    });
  }
  // 7 who cites us
  {
    const f7 = F.f7 || {};
    const n = INST.reduce((s, i) => s + (f7[i]?.flagged?.length || 0), 0);
    const ds = INST.map((i) => `${i} ${pct(f7[i]?.domestic_share, 0)}`).join(" · ");
    out.push({
      id: "f7", n: 7, kicker: "7 · Who cites us but never works with us?", question: "Which Indian institutes use our research heavily but have (almost) no joint papers with us?",
      number: String(n), numberLabel: `Indian institutes in the top 10% by citations to us with ≤ 1 co-authored paper. Domestic share of our citations: ${ds}.`,
      recommendation: "Target these institutes for MoUs, joint projects and visiting positions — they already build on our work.",
      audience: "Outreach and partnerships office",
    });
  }
  // order for the Overview: most striking three first
  return out;
}
