# Sanity checklist (from the project lead, 2026-10-12)

Every item is checked by `pipeline/06_qa.py` / `qa/checkpoint*.py` where it can be automated;
the rest are done by hand and recorded in `qa/qa_report.md`.

## Checkpoint 1 — roster
- Total count vs NIRF submission / annual report per institute (gap > ~10% = missed pages or non-faculty).
- Wrong people: PhD students, postdocs, staff, lab managers, "Dr." duplicates; search for "Scholar", "Engineer", "Officer".
- Units: every centre/department has people; nobody counted twice (one row, secondary unit).
- Spot-check 10 known names: unit, designation, joining year (2+ wrong = scraper misreading).
- Joining years: none before founding (IIIT-H 1998, IIIT-D 2008), none in the future; share inferred vs stated.
- Former faculty are real departures (not a website redesign): confirm a few moved elsewhere.

## Checkpoint 2 — author matching
- Match rate per institute > 90%; inspect every unmatched person.
- Paper counts vs DBLP/Scholar for 10 faculty within ~±20% (higher = merge, lower = missed split).
- Common names and most prolific faculty first (wrong merges top every ranking).
- Topic coherence (CV professor with chemistry/clinical papers = wrong merge).
- No OpenAlex author ID assigned to two faculty.
- Affiliation timeline: many institute-affiliated papers years before joining = wrong joining year or match.

## Checkpoint 3 — full data
- Papers per year smooth (dip = failed download; low 2026 expected).
- Top 5 most prolific by hand (> ~40 papers/year suspicious).
- Journal vs conference split: conferences a large share (else DBLP merge failed).
- No duplicates (sort by title; no arXiv next to published version).
- Ranking coverage: share of journals with quartile, conferences with CORE; top 20 venues plausible per unit.
- Top-10 most-cited plausible (OpenAlex < Scholar is normal).
- Indian flags: TRUE share strictly between 0% and 100%; hand-check 5 papers incl. one cited only by own institute (must be FALSE).
- Network files: every citation source paper exists in papers; no self-loops; no A–B + B–A duplicates; no institute as its own partner.
- Format: exact file names, columns, order; group = 9 on every row; opens in Excel with correct encoding (Hindi/accents).
- Audit sample: 50 random papers vs publisher page; < 5% errors solid, > 10% find the pattern.

## After analysis
- Network size: nodes = faculty with ≥ 1 paper; report isolated faculty and giant-component share.
- Robustness: rerun key results without large-team papers and with preprints; flag findings that flip.
- Small groups: flag units with < 5 faculty.
- Hand-check one number per finding by recomputing from the workbook.

## Website
- Numbers match the workbook (spot-check headlines).
- Filters add up: IIIT-H + IIIT-D = both.
- 2026 marked partial.
- Works when shared: zipped site offline, on another laptop and a phone.
