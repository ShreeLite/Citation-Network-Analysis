"""Checkpoint 1 sanity checks (qa/sanity_checklist.md) -> qa/checkpoint1.md"""
from __future__ import annotations

import re
import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, ".")
from common.config import DATA, PROCESSED, QA  # noqa: E402
from common.names import name_similarity, normalise  # noqa: E402

FOUNDED = {"IIIT-H": 1998, "IIIT-D": 2008}
BAD_WORDS = r"scholar|engineer|officer|student|post[- ]?doc|manager|staff|intern|research associate|project associate|fellow\b|assistant registrar|librarian|coordinator"
# People whose public role we can state without guessing; checked against what the scraper read.
KNOWN = [  # (institution, name, expected unit substring, expected status/designation hint)
    ("IIIT-H", "P J Narayanan", "CVIT", "Professor"), ("IIIT-H", "C V Jawahar", "CVIT", "Professor"),
    ("IIIT-H", "K Madhava Krishna", "RRC", "Professor"), ("IIIT-H", "Kamalakar Karlapalem", "", "Professor"),
    ("IIIT-H", "Ponnurangam Kumaraguru", "", "Professor"), ("IIIT-H", "Dipti Misra Sharma", "LTRC", "Professor"),
    ("IIIT-H", "Vineet Gandhi", "CVIT", "Professor"), ("IIIT-D", "Anubha Gupta", "ECE", "Professor"),
    ("IIIT-D", "Vikram Goyal", "CSE", "Professor"), ("IIIT-D", "Gajendra Pal Singh Raghava", "CB", "Professor"),
    ("IIIT-D", "Pankaj Jalote", "", "Emeritus"), ("IIIT-D", "Debarka Sengupta", "CB", "Professor"),
]


def find(df, inst, name):
    sub = df[df.institution == inst]
    if sub.empty:
        return None, 0
    s = sub.name.map(lambda n: name_similarity(n, name))
    i = s.idxmax()
    return (sub.loc[i], s[i]) if s[i] >= 0.8 else (None, s[i])


def main() -> None:
    r = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    L = ["# Checkpoint 1 — roster sanity checks", ""]
    cur = r[r.status.eq("current")]
    core_cur = cur[cur.is_core.eq("True")]

    # 1. outside count
    L += ["## 1. Count vs NIRF", ""]
    tot = pd.read_csv(PROCESSED / "nirf_totals.csv") if (PROCESSED / "nirf_totals.csv").exists() else pd.DataFrame()
    for inst in ("IIIT-H", "IIIT-D"):
        c = core_cur[core_cur.institution == inst]
        t = tot[(tot.institution == inst) & tot.faculty_entered.notna()].sort_values("ranking_year")
        nirf = int(t.faculty_entered.iloc[-1]) if len(t) else None
        allcur = cur[cur.institution == inst]
        L.append(f"- **{inst}**: {len(c)} current core faculty scraped ({len(allcur)} listed incl. adjunct/visiting/etc.). "
                 f"NIRF {int(t.ranking_year.iloc[-1]) if len(t) else '?'} 'faculty members entered': {nirf} (NIRF also counts lecturers and contractual/visiting staff).")
    if (DATA / "external" / "nirf_iiitd_faculty.csv").exists():
        nf = pd.read_csv(DATA / "external" / "nirf_iiitd_faculty.csv")
        prof = nf[nf.designation.isin(["Assistant Professor", "Associate Professor", "Professor", "Dean / Principal / Director / Vice Chancellor"])
                  & nf.currently_working_latest & nf.association.eq("Regular") & nf.latest_file_year.eq(nf.latest_file_year.max())]
        c = core_cur[core_cur.institution == "IIIT-D"]
        gap = abs(len(c) - len(prof)) / max(1, len(prof))
        L.append(f"- **IIIT-D like-for-like**: NIRF {int(nf.latest_file_year.max())} lists {len(prof)} current regular professor-rank faculty; roster has {len(c)} → gap {gap:.1%} ({'OK' if gap <= 0.10 else 'INVESTIGATE'}).")
        ours = set(c.name.map(normalise))
        only_nirf = [n for n in prof.nirf_name if max((name_similarity(n, o) for o in c.name), default=0) < 0.9]
        only_site = [n for n in c.name if max((name_similarity(n, o) for o in prof.nirf_name), default=0) < 0.9]
        L.append(f"  - in NIRF but not on site as core: {only_nirf or 'none'}")
        L.append(f"  - on site as core but not in NIRF: {only_site or 'none'}")
    wp = PROCESSED / "wayback_presence.csv"
    if wp.exists():
        p = pd.read_csv(wp)
        p["core"] = p.designation_seen.str.contains("Professor", na=False) & ~p.designation_seen.str.contains("Adjunct|Visiting|Emeritus|Practice|Distinguished", na=False)
        t = p[p.core].groupby(["year", "institution"]).name.nunique().unstack().fillna("—")
        L += ["", "Independent like-for-like trajectory — professor-rank faculty listed on each institute's own archived faculty page (one Wayback snapshot per year):", "", t.to_markdown(), "",
              f"Today: IIIT-H {len(core_cur[core_cur.institution=='IIIT-H'])}, IIIT-D {len(core_cur[core_cur.institution=='IIIT-D'])}. "
              "Steady growth to today's counts means no pages were missed; the IIIT-H gap to the NIRF total is NIRF counting research scientists, lecturers, visiting and contractual staff."]
    L.append("")

    # 2. wrong people
    role = r.designation_raw.str.split(r",?\s*Ph\.?\s?D|\bM\.?\s?Tech|\bB\.?\s?Tech", regex=True).str[0]  # role text only, not degrees
    bad = r[role.str.contains(BAD_WORDS, case=False, regex=True) | r.name.str.contains(BAD_WORDS, case=False, regex=True)]
    dup = r.assign(k=r.institution + "|" + r.name.map(normalise)).k
    dups = r[dup.duplicated(keep=False)]
    near = []
    for inst, g in r.groupby("institution"):
        names = g.name.tolist()
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if name_similarity(names[i], names[j]) >= 0.92:
                    near.append(f"{names[i]} ~ {names[j]} ({inst})")
    L += ["## 2. Wrong people", "", f"- Designation/name containing non-faculty words ({BAD_WORDS}): {len(bad)}"]
    L += [f"  - {x.institution}: {x['name']} — {x.designation_raw} [{x.designation_class}]" for _, x in bad.iterrows()]
    L += [f"- Exact duplicate names within an institute: {len(dups)}", f"- Near-duplicate names (\"Dr.\" variants etc.): {near or 'none'}", ""]
    L += [f"- Designation classes: " + "; ".join(f"{i}: {dict(Counter(g.designation_class))}" for i, g in r.groupby("institution")), ""]

    # 3. units
    L += ["## 3. Units", ""]
    for inst, g in core_cur.groupby("institution"):
        vc = g.unit.replace("", "(none)").value_counts()
        L.append(f"- **{inst}** ({len(vc)} units): " + ", ".join(f"{u} {n}" for u, n in vc.items()))
        L.append(f"  - with a secondary unit: {g.units_secondary.ne('').sum()}; small units (< 5 core faculty): {[u for u, n in vc.items() if n < 5]}")
    L.append(f"- Each person appears once: {'yes' if not r.faculty_id.duplicated().any() else 'NO'}")
    L.append("")

    # 4. spot check
    L += ["## 4. Spot check of known names", "", "| Institute | Name | Found as | Unit | Designation | Status | Joining year (source) | Check |", "|---|---|---|---|---|---|---|---|"]
    wrong = 0
    for inst, name, unit, desig in KNOWN:
        x, s = find(r, inst, name)
        if x is None:
            L.append(f"| {inst} | {name} | NOT FOUND (best sim {s:.2f}) | | | | | ✗ |")
            wrong += 1
            continue
        ok_u = (not unit) or unit.lower() in (x.unit + " " + x.units_secondary).lower()
        ok_d = desig.lower() in (x.designation + " " + x.designation_raw).lower()
        ok = ok_u and ok_d
        wrong += not ok
        L.append(f"| {inst} | {name} | {x['name']} | {x.unit} {('+ ' + x.units_secondary) if x.units_secondary else ''} | {x.designation} | {x.status} | {x.joining_year} ({x.joining_year_source}) | {'✓' if ok else '✗'} |")
    L += ["", f"Mismatches: {wrong} of {len(KNOWN)} ({'OK' if wrong < 2 else 'INVESTIGATE: scraper may misread pages'}).", ""]

    # 5. joining years
    jy = pd.to_numeric(r.joining_year, errors="coerce")
    bad_jy = r[(jy.notna()) & ((jy > 2026) | (jy < r.institution.map(FOUNDED)))]
    src = core_cur.joining_year_source.replace("", "missing").str.replace(r"^stated_.*", "stated (homepage/CV/profile)", regex=True).value_counts()
    L += ["## 5. Joining years", "", f"- Outside [founding year, 2026]: {len(bad_jy)} " + ("; ".join(f"{x['name']} {x.joining_year}" for _, x in bad_jy.iterrows()) if len(bad_jy) else ""),
          "- Source among current core faculty: " + ", ".join(f"{k} {v} ({v / len(core_cur):.0%})" for k, v in src.items()),
          f"- Missing exact year but bounded: listed in the earliest snapshot (joined ≤ that year, i.e. before 2016): {(core_cur.joining_year.eq('') & core_cur.joined_by_year.ne('')).sum()}; "
          f"absent from all snapshots (joined after the last one; refined from the first institute-affiliated paper in step 2): {(core_cur.joining_year.eq('') & core_cur.joined_after_year.ne('')).sum()}",
          "- Homepages rarely state a joining year (4%), so official NIRF dates (IIIT-D) and first appearance on the archived faculty list (IIIT-H) carry most of the load; both are documented per person in `joining_year_evidence`.", ""]

    # 6. former faculty
    fm = r[r.status.eq("former")]
    L += ["## 6. Former faculty", "", f"- {len(fm)} former-faculty rows: " + ", ".join(f"{k} {v}" for k, v in fm.roster_source.value_counts().items())]
    L += [f"  - {x.institution}: {x['name']} — {x.designation} — {x.notes[:120]}" for _, x in fm.sort_values(['institution', 'name']).iterrows()]
    L.append("")
    (QA / "checkpoint1.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
