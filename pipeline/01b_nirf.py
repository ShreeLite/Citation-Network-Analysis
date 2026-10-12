"""Step 1b — Merge NIRF data into the roster.

  * IIIT-D: per-faculty NIRF tables (2022–2026 DCS files on iiitd.ac.in) give official joining
    and leaving dates. They override homepage-parsed joining years (conflicts > 1 year go to
    review), confirm Wayback former-faculty candidates, and add departures the website no
    longer lists.
  * Both: NIRF 'faculty members entered' totals (nirfindia.org) for the outside count check.
    IIIT-H's per-faculty tables live under /wp-content/, which iiit.ac.in's robots.txt
    disallows, so IIIT-H is checked on totals only.
"""
from __future__ import annotations

import pandas as pd

from common.config import DATA, EXTERNAL, PROCESSED, REVIEW, cfg, setup_logging
from common.names import name_similarity, normalise
from common.nirf import iiitd_faculty, summary_totals

log = setup_logging("01b_nirf")
Y0, Y1 = cfg()["years"]["start"], cfg()["years"]["end"]
PROF_RANKS = {"Assistant Professor", "Associate Professor", "Professor", "Dean / Principal / Director / Vice Chancellor"}


def _s(v) -> str:
    """Roster columns are strings (pandas 3 enforces string dtype)."""
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)


def year_of(d: str | None) -> int | None:
    return int(d[-4:]) if d and d[-4:].isdigit() else None


def consolidate(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["key"] = df.name.map(normalise)
    out = []
    for key, g in df.groupby("key"):
        g = g.sort_values("ranking_year")
        last = g.iloc[-1]
        joins = g.joining_date.map(year_of).dropna()
        leaves = g.leaving_date.dropna().map(year_of).dropna()
        out.append({"nirf_name": last["name"], "key": key, "designation": last.designation, "association": last.association,
                    "joining_year": int(joins.mode().iloc[0]) if len(joins) else None,
                    "joining_dates_seen": "; ".join(sorted(set(g.joining_date))),
                    "leaving_year": int(leaves.max()) if len(leaves) else None,
                    "currently_working_latest": bool(last.currently_working) and not len(leaves),
                    "latest_file_year": int(last.ranking_year), "first_file_year": int(g.ranking_year.min()),
                    "qualification": last.qualification})
    return pd.DataFrame(out)


def main() -> None:
    roster = pd.read_csv(DATA / "faculty_roster.csv", dtype=str).fillna("")
    totals = pd.DataFrame(summary_totals("IIIT-H") + summary_totals("IIIT-D"))
    totals.to_csv(PROCESSED / "nirf_totals.csv", index=False)

    rows, files = iiitd_faculty()
    pd.DataFrame(rows).to_csv(EXTERNAL / "nirf_iiitd_faculty_rows.csv", index=False)
    nf = consolidate(rows)
    nf.to_csv(EXTERNAL / "nirf_iiitd_faculty.csv", index=False)
    review = []

    d = roster[roster.institution.eq("IIIT-D")]
    matched_keys = set()
    for idx, r in d.iterrows():
        best, bs = None, 0.0
        for n in nf.itertuples():
            s = name_similarity(r["name"], n.nirf_name)
            if s > bs:
                best, bs = n, s
        if not best or bs < 0.9:
            continue
        matched_keys.add(best.key)
        roster.at[idx, "nirf_name"] = _s(best.nirf_name)
        roster.at[idx, "nirf_designation"] = _s(best.designation)
        roster.at[idx, "nirf_joining_year"] = _s(best.joining_year)
        roster.at[idx, "nirf_leaving_year"] = _s(best.leaving_year or "")
        stated = pd.to_numeric(r.joining_year, errors="coerce")
        if best.joining_year:
            if pd.notna(stated) and abs(stated - best.joining_year) > 1:
                review.append({"issue": "joining_year_conflict_nirf_vs_homepage", "institution": "IIIT-D", "name": r["name"],
                               "detail": f"NIRF {best.joining_year} ({best.joining_dates_seen}) vs homepage {int(stated)}: {r.joining_year_evidence[:150]}",
                               "evidence_url": "NIRF DCS", "action": "NIRF used; confirm"})
            roster.at[idx, "joining_year"] = _s(best.joining_year)
            roster.at[idx, "joining_year_source"] = _s("nirf_dcs")
            roster.at[idx, "joining_year_confidence"] = _s(0.95)
            roster.at[idx, "joining_year_evidence"] = _s(f"NIRF joining date(s): {best.joining_dates_seen}")
        if best.leaving_year and r.status == "current" and r.designation_class == "core":
            review.append({"issue": "listed_on_site_but_nirf_says_left", "institution": "IIIT-D", "name": r["name"],
                           "detail": f"NIRF leaving year {best.leaving_year}", "evidence_url": "NIRF DCS", "action": "still current?"})
        latest_year = int(nf.latest_file_year.max())
        if r.status == "former" and best.currently_working_latest and best.latest_file_year == latest_year:
            # dropped off the website list but NIRF says still working (e.g. the Director)
            roster.at[idx, "status"] = _s("current")
            roster.at[idx, "roster_source"] = _s("nirf_current_not_on_faculty_page")
            roster.at[idx, "leaving_year"] = _s("")
            if best.designation in PROF_RANKS:
                roster.at[idx, "designation_class"] = _s("core")
                roster.at[idx, "is_core"] = _s("True")
                roster.at[idx, "designation"] = _s("Professor" if best.designation.startswith("Dean") else best.designation)
            review.append({"issue": "current_per_nirf_not_on_faculty_page", "institution": "IIIT-D", "name": r["name"],
                           "detail": f"NIRF {latest_year}: {best.designation}, working", "evidence_url": "NIRF DCS", "action": "set unit"})
        elif r.status == "former":  # Wayback candidate confirmed by NIRF
            roster.at[idx, "roster_source"] = _s("wayback+nirf")
            roster.at[idx, "designation"] = _s(best.designation if best.designation in PROF_RANKS else r.designation)
            if best.designation in PROF_RANKS:
                roster.at[idx, "designation_class"] = _s("core")
                roster.at[idx, "is_core"] = _s("True")
            roster.at[idx, "leaving_year"] = _s(best.leaving_year or r.leaving_year)

    # NIRF departures not on the roster at all (or only as adjunct) -> add as former core faculty
    added = []
    for n in nf.itertuples():
        if n.key in matched_keys or n.designation not in PROF_RANKS or n.association != "Regular":
            continue
        if not n.leaving_year or not (Y0 <= n.leaving_year <= Y1):
            continue
        added.append({"faculty_id": f"IIIT-D:{n.key.replace(' ', '_')}", "institution": "IIIT-D", "name": n.nirf_name,
                      "name_variants": n.nirf_name, "designation": "Professor" if n.designation.startswith("Dean") else n.designation,
                      "designation_raw": n.designation, "designation_class": "core", "is_core": "True", "unit": "", "unit_type": "department",
                      "status": "former", "joining_year": n.joining_year, "joining_year_source": "nirf_dcs", "joining_year_confidence": 0.95,
                      "joining_year_evidence": f"NIRF joining date(s): {n.joining_dates_seen}", "leaving_year": n.leaving_year,
                      "roster_source": "nirf", "notes": f"NIRF DCS {n.first_file_year}-{n.latest_file_year}; left {n.leaving_year}",
                      "collected_at": roster.collected_at.iloc[0]})
        review.append({"issue": "former_faculty_from_nirf", "institution": "IIIT-D", "name": n.nirf_name,
                       "detail": f"{n.designation}, joined {n.joining_year}, left {n.leaving_year}", "evidence_url": "NIRF DCS",
                       "action": "unit unknown: set department"})
    if added:
        roster = pd.concat([roster, pd.DataFrame(added)], ignore_index=True).fillna("")
    roster.to_csv(DATA / "faculty_roster.csv", index=False)
    old = pd.read_csv(REVIEW / "roster_to_review.csv") if (REVIEW / "roster_to_review.csv").exists() else pd.DataFrame()
    pd.concat([old, pd.DataFrame(review)], ignore_index=True).drop_duplicates().to_csv(REVIEW / "roster_to_review.csv", index=False)
    print(f"NIRF files: {[(f['ranking_year'], f['rows']) for f in files]}")
    print(f"IIIT-D: {len(matched_keys)} roster people matched to NIRF; {len(added)} NIRF departures added as former faculty; {len(review)} review items")
    print(totals.to_string(index=False))


if __name__ == "__main__":
    main()
