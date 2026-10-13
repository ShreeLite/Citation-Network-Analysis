# IIIT Hyderabad × IIIT Delhi — research mapping 2016–2026 (DPCN Group 9)

A reproducible pipeline, analysis and static website mapping every publication by IIIT-H and
IIIT-D faculty from 2016 to 2026 (2026 is a partial year), with citation, co-authorship and
Indian-connection networks, a "centres vs departments" analysis, and seven actionable findings.

- **Website:** `site/dist/index.html` — one self-contained file; open it directly (works offline,
  from `file://`) or host the `site/dist/` folder anywhere static.
- **Data:** `deliverables/group9_deliverables.zip` — official CSVs + formatted Excel workbook + QA report.
- **QA:** `qa/qa_report.md`, `qa/checkpoint1.md`, `qa/checkpoint2.md`, `qa/checkpoint3.md`.

<!-- RESULTS:START -->
## Results at a glance

Collected 2026-10-12 (2026 partial).

| | IIIT-H | IIIT-D |
|---|---|---|
| Core faculty (current) | 109 | 102 |
| Former core faculty (2016–2026) | 35 | 49 |
| Papers (journal + conference) | 4710 | 4329 |
| Conference share | 61% | 54% |
| NMI official units vs communities | 0.54 | 0.35 |
| Cross-unit share of collaborations | 70% | 38% |

**Quality checks:** dblp pooled recall = 0.7621; dup doi rows = 0.0; dup title rows = 98.0; filled doi = 0.9559; filled quartile (journals) = 0.0; filled CORE rank (conferences) = 0.498; filled quartile proxy (journals) = 0.9606; self loops = 0.0; ab ba duplicates = 0.0; own partner rows = 0.0; audit error rate = 0.0217
Quartiles from: openalex_proxy.

**Deliverables:** `deliverables/group9_deliverables.zip` (28.3 MB) · website `site/dist/index.html`.

QA reports: `qa/checkpoint1.md`, `qa/checkpoint2.md`, `qa/qa_report.md` (checkpoint 3), `qa/robustness.md`, `qa/findings_handcheck.md`, `qa/site_check.md`.
<!-- RESULTS:END -->

## Running it

```bash
make setup                 # venv, Python deps, Chromium (Playwright), npm packages
cp .env.example .env       # add OPENALEX_API_KEY (free: openalex.org/settings/api); S2_API_KEY optional
make core                  # YOU run this: CORE's robots.txt disallows AI agents (see below)
make scimago               # Scimago SJR exports 2016–2025 (browser download)
make all                   # roster → identity → publications → enrich → networks → qa → analysis → deliverables → site
```

Every network call is cached under `data/cache/` (raw responses), rate-limited, retried with
exponential backoff and logged to `data/raw/request_log.jsonl`. Re-running any step re-uses the
cache; a crash or an exhausted OpenAlex daily budget resumes cleanly on the next run.

| Step | Command | Output |
|---|---|---|
| 1 Roster | `make roster` | `data/faculty_roster.csv`, `review/roster_to_review.csv` |
| 2 Identity | `make identity` (`make reingest` after editing the review file) | `data/processed/faculty_author_ids.csv`, `review/author_matches_to_review.csv` |
| 3 Publications | `make pubs` | `data/processed/papers.parquet`, `faculty_paper_links.parquet` |
| 4 Enrichment | `make enrich` | `data/processed/papers_enriched.parquet`, `data/external/venue_map.csv` |
| 5 Networks | `make networks` | `citation_network.csv`, `authorship_network.csv`, `indian_connections.csv` |
| 6 QA | `make qa` | `qa/qa_report.md`, `review/audit_sample.csv` |
| Analysis | `make analysis` | `site/src/data/*.json`, `data/processed/analysis/*.csv`, `report_figures/*.png` |
| Deliverables | `make deliverables` | `deliverables/` |
| Website | `make site` | `site/dist/index.html` |
| Tests | `make test` | pytest: names, titles, dedup, venues, partners, robots, graphs, joining years |

## Sources and access decisions

| Source | Used for | Access notes |
|---|---|---|
| Institute websites (iiit.ac.in, iiitd.ac.in) | roster, units, designations, homepages | crawled from the homepages; robots.txt obeyed with RFC 9309 longest-match rules (also for `Claude-User`); IIIT-D's `Crawl-delay: 10` honoured; IIIT-D's incomplete TLS chain repaired via AIA (verification never disabled) |
| NIRF (nirfindia.org, iiitd.ac.in) | outside faculty counts; IIIT-D joining/leaving dates | IIIT-H's per-faculty NIRF tables are under `/wp-content/`, which its robots.txt disallows, so IIIT-H is checked on totals only |
| Wayback Machine (CDX) | former faculty | one snapshot per year 2016–2025 of each faculty-list page |
| OpenAlex (API key) | works, authors, institutions, topics, references, citations | credit-metered; list calls batched (≤ 100 IDs), free singleton fallback when the daily budget runs out; `per_page` ≤ 100 |
| DBLP (SPARQL endpoint) | CS publication lists, record types, ORCIDs | the dblp.org HTML/XML/JSON API sits behind a bot-check; we use the official SPARQL endpoint (allowed by its robots.txt) |
| Crossref | DOIs, ISSNs, container titles, types | polite pool (mailto) |
| Semantic Scholar | secondary citation counts | keyless, best-effort; coverage reported in QA |
| IIIT-H publications portal | institute-reported records, CORE labels, journal flag | read-only search endpoint |
| Scimago SJR | journal quartiles | 403 to scripts; fetched in a browser session with the project lead's institutional permission (robots.txt allows) |
| CORE portal | conference ranks | robots.txt disallows AI agents, so `make core` is run by a person, never by the automated pipeline |
| IRINS | roster cross-check | 403 to scripts; browser fetch with permission where possible |

## Analytic choices

See the **Data & Methods** tab on the website for the full list. In short: core faculty only
(Assistant/Associate/Full Professor); papers count when the faculty member lists the institute
on the paper or the paper falls on/after their joining year; arXiv versions are merged into the
published paper and arXiv-only works are excluded by default; co-authorship edges are faculty-only
with weight Σ 1/(n_authors − 1); Louvain communities (seed 42); configuration-model null with
degree-preserving rewiring; both a dataset h-index and a lifetime h-index are reported.
`group9_data.csv` has one row per (faculty author, paper) — a paper with two of our faculty
appears twice, as the spec's `author` column implies; the `papers` sheet has one row per paper.

## Required dashboard panels → where they live

| # | Required panel | Website tab |
|---|---|---|
| 1 | Publication trend 2016–2026 | Overview, Publications |
| 2 | Q1 fraction per institution (with CORE A*/A share) | Venues & Quality, Overview |
| 3 | Faculty h-index distribution | Faculty |
| 4 | Faculty list and performance table | Faculty |
| 5 | Top 5 journals and conferences per institution | Venues & Quality, Publications |
| 6 | Top 10 most-cited papers | Publications |
| 7 | Research area breakdown | Research Areas |
| 8 | Citation network (in-degree, PageRank, flow) | Citation Network |
| 9 | Authorship network (degree, betweenness, communities, bridges) | Collaboration Network, Centres vs Departments |
| 10 | Citation flow with Indian institutes | Indian Connections |
| 11 | Connectivity map of Indian partners | Indian Connections, Findings (7) |

## Hosting

- **Offline / email:** send `site/dist/index.html` together with `group9_deliverables.zip` (same folder). Double-click the HTML.
- **GitHub Pages:** push `site/dist/` to a `gh-pages` branch (or set Pages to serve `/site/dist`).
- **Netlify:** drag-and-drop the `site/dist/` folder onto app.netlify.com/drop.

## Repository layout

```
config.yaml   pipeline/   analysis/   common/   tests/   scripts/
data/{raw,cache,external,processed}/   review/   qa/   deliverables/   report_figures/   site/
```
