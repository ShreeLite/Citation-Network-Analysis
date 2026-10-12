"""Checkpoint 2 sanity checks (author matching) -> qa/checkpoint2.md, qa/checkpoint2_flags.csv"""
from __future__ import annotations

import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, ".")
from common.config import DATA, PROCESSED, QA, cfg  # noqa: E402
from common.dblp_parse import person_publications, prefetch  # noqa: E402
from common.sources import oa_get  # noqa: E402

Y0, Y1 = cfg()["years"]["start"], cfg()["years"]["end"]
CS_LIKE = {"Computer Science", "Engineering", "Mathematics", "Decision Sciences", "Physics and Astronomy", "Social Sciences",
           "Arts and Humanities", "Psychology", "Neuroscience", "Biochemistry, Genetics and Molecular Biology", "Economics, Econometrics and Finance"}


def oa_count(ids: list[str]) -> int:
    res = oa_get("works", filter=f"author.id:{'|'.join(ids)},publication_year:{Y0}-{Y1},type:article|proceedings-article|book-chapter", **{"per-page": 1})
    return res.get("meta", {}).get("count", 0)


def main() -> None:
    r = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    acc = pd.read_csv(PROCESSED / "faculty_author_ids.csv", dtype=str)
    cands = pd.read_parquet(PROCESSED / "author_candidates.parquet")
    core = r[r.is_core.eq("True")]
    ids = acc.groupby("faculty_id").author_id.apply(list).to_dict()
    L = ["# Checkpoint 2 — author matching sanity checks", ""]
    flags = []

    # 1. match rate
    L += ["## 1. Match rate", ""]
    for inst, g in core.groupby("institution"):
        for st, gg in g.groupby("status"):
            m = gg.faculty_id.isin(ids)
            L.append(f"- {inst} {st}: {m.sum()}/{len(gg)} matched ({m.mean():.1%}) {'OK' if m.mean() >= 0.9 else 'BELOW 90%'}")
        un = g[~g.faculty_id.isin(ids)]
        for _, x in un.iterrows():
            best = cands[cands.faculty_id == x.faculty_id].sort_values("confidence", ascending=False).head(1)
            why = f"best candidate {best.author_name.iloc[0]} ({best.author_id.iloc[0]}, conf {best.confidence.iloc[0]}, {best.reason.iloc[0]}, works {best.works_count.iloc[0]})" if len(best) else "no OpenAlex candidate with a similar name"
            L.append(f"  - unmatched: {x['name']} ({x.unit or 'no unit'}, {x.status}) — {why}")
            flags.append({"check": "unmatched", "faculty": x["name"], "institution": inst, "detail": why})
    L.append("")

    # 2. DBLP vs OpenAlex counts for 10 faculty (5 most prolific in DBLP + 5 random)
    withp = core[core.dblp_pid.ne("") & core.faculty_id.isin(ids)]
    prefetch(withp.dblp_pid.tolist())
    rows = []
    for _, x in withp.iterrows():
        d = person_publications(x.dblp_pid)
        n_dblp = sum(1 for rec in d["records"] if rec["year"] and Y0 <= rec["year"] <= Y1 and rec["dblp_type"] in ("journal", "conference"))
        rows.append((x, n_dblp))
    rows.sort(key=lambda t: -t[1])
    sample = rows[:5] + [rows[i] for i in range(5, len(rows), max(1, (len(rows) - 5) // 5))][:5]
    L += ["## 2. Paper counts vs DBLP (2016–2026, journal + conference)", "", "| Faculty | Inst. | DBLP | OpenAlex (matched IDs) | Ratio | Check |", "|---|---|---|---|---|---|"]
    for x, n_dblp in sample:
        n_oa = oa_count(ids[x.faculty_id])
        ratio = n_oa / n_dblp if n_dblp else float("nan")
        ok = 0.8 <= ratio <= 1.2
        L.append(f"| {x['name']} | {x.institution} | {n_dblp} | {n_oa} | {ratio:.2f} | {'✓' if ok else ('MERGE?' if ratio > 1.2 else 'SPLIT MISSED?')} |")
        if not ok:
            flags.append({"check": "count_vs_dblp", "faculty": x["name"], "institution": x.institution, "detail": f"DBLP {n_dblp} vs OpenAlex {n_oa}"})
    L += ["", "OpenAlex also indexes non-CS venues DBLP does not cover, so ratios somewhat above 1 are expected for interdisciplinary faculty.", ""]

    # 3. common surnames and most prolific
    c2 = cands.merge(acc[["faculty_id", "author_id"]])
    tot = c2.groupby("faculty_id").works_count.sum().sort_values(ascending=False)
    sur = Counter(n.split()[-1].lower() for n in core.name if n.split())
    common = {s for s, k in sur.items() if k >= 2} | {"kumar", "sharma", "singh", "gupta", "reddy", "rao", "jain", "agarwal", "das"}
    L += ["## 3. Most prolific and common-surname faculty (merge risk)", "", "| Faculty | IDs | Lifetime works (sum over IDs) | Lifetime h | Top topics |", "|---|---|---|---|---|"]
    look = list(tot.index[:10]) + [f for f in core.faculty_id if f in ids and f.split(":")[1].split("_")[-1] in common]
    for f in dict.fromkeys(look):
        g = c2[c2.faculty_id == f]
        L.append(f"| {r.set_index('faculty_id').at[f, 'name']} | {len(g)} | {int(g.works_count.sum())} | {g.h_index_lifetime.max()} | {'; '.join(g.top_topics.head(2))[:90]} |")
    L.append("")

    # 4. topic coherence
    L += ["## 4. Topic coherence", ""]
    inc = 0
    for f, g in c2.groupby("faculty_id"):
        fields = [t for t in g.top_topics for t in t.split("; ")]
        if not fields:
            continue
        unit = r.set_index("faculty_id").at[f, "unit"]
        odd = [t for t in fields if any(w in t.lower() for w in ("clinical", "cancer", "chemistry", "catalys", "surgery", "patient", "veterinar", "agricultur", "polymer"))]
        if odd and unit not in ("CB", "CCNSB", "CSTAR"):
            inc += 1
            flags.append({"check": "topic_incoherent", "faculty": r.set_index('faculty_id').at[f, 'name'], "institution": f.split(":")[0], "detail": f"unit {unit}; topics {odd[:3]}"})
            L.append(f"- {r.set_index('faculty_id').at[f, 'name']} ({unit}): {odd[:3]}")
    L += [f"- {inc} faculty with topics far from their unit (computational biology/chemistry units excluded).", ""]

    # 5. shared ids
    sh = acc.groupby("author_id").faculty_id.nunique()
    L += ["## 5. Shared OpenAlex IDs", "", f"- IDs assigned to more than one faculty member: {int((sh > 1).sum())} {'OK' if (sh > 1).sum() == 0 else 'FIX'}", ""]

    # 6. affiliation timeline
    L += ["## 6. Affiliation before joining", ""]
    n_early = 0
    for f, g in c2.groupby("faculty_id"):
        jy = pd.to_numeric(r.set_index("faculty_id").at[f, "joining_year"], errors="coerce")
        if pd.isna(jy):
            continue
        yrs = sorted({int(y) for s in g.affiliated_years for y in str(s).split(",") if y})
        early = [y for y in yrs if y < jy - 1]
        if len(early) >= 3:
            n_early += 1
            flags.append({"check": "affiliated_years_before_joining", "faculty": r.set_index('faculty_id').at[f, 'name'], "institution": f.split(":")[0],
                          "detail": f"joined {int(jy)} ({r.set_index('faculty_id').at[f, 'joining_year_source']}); institute-affiliated papers in {early}"})
    L += [f"- {n_early} faculty with institute-affiliated papers ≥ 3 distinct years before joining (often IIIT alumni who did their PhD there; listed in qa/checkpoint2_flags.csv).", ""]

    (QA / "checkpoint2.md").write_text("\n".join(L))
    pd.DataFrame(flags).to_csv(QA / "checkpoint2_flags.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()
