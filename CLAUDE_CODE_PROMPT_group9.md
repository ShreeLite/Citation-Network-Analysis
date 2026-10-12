# DPCN Research Mapping Project — Group 9 (IIIT Hyderabad + IIIT Delhi)

You are building a complete research-mapping project for a university course (DPCN, Dynamical Processes in Complex Networks; instructor Chittaranjan Hens). Read this whole file before writing code. Work in plan mode first and show me the plan.

**Priority order, never reverse it:**
1. **Fool-proof data.** Every faculty member, every paper 2016–2026, correctly attributed, deduplicated, enriched, and verified. Completeness and accuracy matter more than speed. Use every legitimate source and cross-check them against each other.
2. **A formal, sleek, static website** presenting the required panels, the central question, and seven actionable findings, with tabs, global filters, and interactive charts and networks.
3. **Downloadable data**: an Excel workbook plus the official CSVs, zipped, ready to email.

The professor wants **simple metrics** (degree, betweenness, components, communities, citation counts) used to find **new, important, actionable** results. Every finding must end in a recommendation and name who would act on it.

My contact email for API polite pools: `krisjainhzb@gmail.com`. If any API now requires a free key (OpenAlex, Semantic Scholar), stop and ask me for it.

---

## 0. Ground rules

- **Scope:** institutions are IIIT Hyderabad (International Institute of Information Technology, Hyderabad) and IIIT Delhi (Indraprastha Institute of Information Technology Delhi). Years 2016–2026 inclusive. 2026 is partial; mark it as such everywhere.
- **Analysis stays within IIIT-H and IIIT-D.** Links to other Indian institutes appear in the raw files and in the required citation-flow and connectivity panels only. Never merge data from other groups.
- **Reproducible and resumable:** every network call is cached to disk (raw JSON), retried with exponential backoff, rate-limited, and logged. Re-running a step must not re-download what is cached. A crash mid-run must resume cleanly.
- **Provenance on every row:** which source(s) each paper and each field came from, and the collection date.
- **Never silently guess.** When something is ambiguous (author identity, venue rank, joining year), record a confidence value and send it to a review CSV for me.
- **Respect sites:** obey robots.txt, use polite delays, identify with a User-Agent containing my email. Do not scrape Google Scholar or LinkedIn (they block and forbid it); at most use Scholar profile links found on faculty pages as manual spot-check references.
- Use Python 3.11+, a `requirements.txt`, and a `Makefile` (or `run_all.py`) so the full pipeline runs with one command. Commit to git at each checkpoint.

---

## 1. Data pipeline (the most important part)

### Step 1 — Faculty roster (both institutes)

Build `data/faculty_roster.csv` with: `institution, name, name_variants, designation, unit, unit_type (centre/department), joining_year, joining_year_source, status (current/former), homepage, email_domain, orcid, dblp_pid, scholar_url, openalex_ids, notes`.

- **Scrape the official faculty pages** of both institutes. Discover the pages by crawling from the homepages; do not hardcode URLs that may have moved. Use `requests` + `BeautifulSoup`, and **Playwright** for any JavaScript-rendered pages.
- **IIIT-H is organised by research centres and labs** (e.g. CVIT, LTRC, Robotics Research Center, CSTAR, SERC, CVEST, CCNSB, Data Sciences/CDE, Spatial Informatics, Cognitive Science, Human Sciences; confirm the actual current list from the site). **IIIT-D is organised by departments** (CSE, ECE, Computational Biology, Mathematics, HCD, SSH; confirm from the site). Record each person's primary unit, and secondary units where listed. This label is essential for the central question.
- **Visit every faculty homepage** to extract ORCID, DBLP link, Scholar link, CV link, and joining year ("Assistant Professor since 2017", CV entries, etc.).
- **Catch former faculty** who were there during 2016–2026 but are no longer listed: query Wayback Machine snapshots of the faculty pages (e.g. one per year 2016–2025) via the CDX API and diff the name lists. Mark them `status=former`.
- **Joining year fallback:** if no stated year, use the year of their first paper with an IIIT-H/IIIT-D affiliation in OpenAlex, and set `joining_year_source=inferred_first_affiliated_paper`.
- Keep core faculty (Assistant/Associate/Full Professor) as the main set. Keep adjunct, visiting, and emeritus with their designation so they can be filtered, but exclude them from the default analysis.
- Cross-check the roster against IRINS profiles for these institutes if IRINS has them.

**CHECKPOINT 1:** Show me roster counts per institute and unit, the list of former faculty found, and the people with missing joining year. Wait for my approval.

### Step 2 — Author identity resolution

For each faculty member, find **all** their OpenAlex author IDs (OpenAlex often splits one person into several profiles, and sometimes merges two people).

- Resolve both institutes' **ROR IDs** via the ROR API and the matching OpenAlex institution IDs (including any lineage/child IDs). Verify; do not hardcode from memory.
- Matching evidence, strongest first: ORCID from homepage → DBLP PID cross-linked papers (match DOIs/titles between DBLP and OpenAlex) → OpenAlex author search filtered by the institution, with fuzzy name matching (handle initials, "Kumar"/"K.", reordered South-Indian names, middle names) → topic overlap with the unit's area.
- Compute a confidence score per (faculty, author ID) pair. Auto-accept high confidence; write everything else to `review/author_matches_to_review.csv` with candidate IDs, sample paper titles, affiliations, and works count.
- Detect over-merged profiles: papers far outside the person's field or with affiliations they never held. Filter those papers individually rather than dropping the whole profile.

**CHECKPOINT 2:** Show me the match rate, the review file, and any faculty with zero matched IDs. Wait for me to correct the review file, then re-ingest it.

### Step 3 — Publications, from multiple sources

Collect each faculty member's works for 2016–2026 from **all** of these, then merge:

1. **OpenAlex** (primary): works by author IDs, `publication_year:2016-2026`, cursor pagination, `per-page=200`, batching up to 50 author IDs per request with `|`. Keep the full work JSON in cache.
2. **DBLP** (essential for CS conferences): fetch each person's publication list by DBLP PID (XML/JSON). DBLP covers NeurIPS, CVPR, ACL, etc. far better than most sources.
3. **Crossref**: fill missing DOIs, ISSNs, venue names, and publication types by DOI or title search.
4. **Semantic Scholar API** (optional, rate-limited): fill missing citation counts and references for papers OpenAlex lacks.

**Merging and deduplication:**
- Match across sources by DOI first, then by normalised title (lowercase, strip punctuation and stopwords) + year ±1 + at least one shared author, using fuzzy matching (rapidfuzz, threshold tuned and reported).
- **Collapse arXiv preprints into their published version** when both exist. Keep arXiv-only works with `type=preprint` and exclude them from the main analysis by default (configurable flag), since the professor may rule either way.
- A paper with several of our faculty appears once in the papers table, with a separate faculty–paper link table. The official `group9_data.csv` has one row per (faculty author, paper) as the spec's `author` column implies; document this choice.
- **Affiliation check:** keep a paper for a faculty member if the paper lists IIIT-H/IIIT-D for them, **or** it falls on/after their joining year. Store flags `affiliated_on_paper` and `within_tenure`. Papers before joining with no institute affiliation go to a separate "pre-joining" sheet, not the main set.
- Store `sources` (e.g. `openalex;dblp`) per paper.

### Step 4 — Enrichment

- **type**: `journal` or `conference` from OpenAlex source type + DBLP record type (`journals/` vs `conf/`) + Crossref type. Resolve conflicts with DBLP winning for CS venues.
- **Venue normalisation**: map long proceedings names to canonical venues and acronyms (e.g. "Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition" → CVPR). Build `data/external/venue_map.csv` automatically, then hand-check the top 150 venues by paper count.
- **Journal quartile**: download the Scimago (SJR) journal rankings CSVs for 2016–2025, join by ISSN (print and electronic), and use the quartile for the paper's year (nearest available year if missing). Record the subject category used (best quartile across categories; document it).
- **Conference rank**: download the CORE conference rankings export (latest edition, plus older editions if available), match by acronym and fuzzy title, with a manual override CSV. Most groups will leave these empty; we must not.
- **citations**: OpenAlex `cited_by_count` at collection date; also store the Semantic Scholar count where available and the max/mean as extra columns.
- **Topics**: OpenAlex primary topic, subfield, field, and domain per paper; per-faculty topic sets for the Jaccard analysis.
- **coauthor_institutes**: semicolon-separated distinct institutions of all co-authors (from OpenAlex authorships), with country codes kept in a parallel column.
- **cites_indian_inst**: fetch every referenced work's institutions in batches of 50 IDs (`filter=openalex_id:W1|W2|...`). TRUE if any cited paper has an Indian (country_code IN) institution **other than the citing paper's own institute**. Also store the list and count.
- **cited_by_indian_inst**: for each paper, query works that cite it (`filter=cites:Wxxx`) restricted to Indian institutions, using `group_by=authorships.institutions.id` to get counts per institution efficiently. TRUE if any Indian institution other than the paper's own institute cites it. Store per-institution counts for the citation-flow analysis.
- **Partner classification**: classify every Indian partner institution into IIT / NIT / IIIT / IISER / IISc-TIFR / CSIR / DAE / Central University / State University / Private / Other, using name rules plus a hand-checked mapping file, for the cross-cluster panel.
- **h-index**: compute two values and label both clearly: (a) h-index within our 2016–2026 dataset, (b) lifetime h-index from OpenAlex author summary stats.

### Step 5 — Network files (exact spec columns, plus extras)

- `citation_network.csv`: `source_doi, target_doi, source_inst, target_inst, year` plus `source_openalex_id, target_openalex_id, internal_edge (bool)`. Keep edges to outside papers with their institutions. If a DOI is missing, fall back to the OpenAlex ID.
- `authorship_network.csv`: `author_a, author_b, paper_doi, inst_a, inst_b, year` plus `cross_institution (bool), n_authors, weight = 1/(n_authors-1)`. Produce two versions: faculty-only (main analysis) and all co-authors (raw). Flag papers with more than 25 authors and down-weight them so one huge paper does not dominate.
- `indian_connections.csv`: `your_inst, partner_inst, shared_papers, total_citations` where `total_citations` = citations received from that partner; add `citations_given_to_partner`, `partner_type`, and `topic_jaccard`.

### Step 6 — Validation and QA (must be automated and reported)

Generate `qa/qa_report.md` and a QA sheet containing:
- **DBLP spot check**: for every faculty member with a DBLP PID, compare our paper count (2016–2026, non-preprint) to DBLP's. Report the overall and per-person match rate and list the worst 20.
- **Random audit sample**: 50 random papers with all fields, exported to `review/audit_sample.csv` for manual verification.
- Duplicate check (same DOI or near-identical title), missing-field rates per column (DOI, ISSN, quartile, CORE rank), faculty with zero or suspiciously many papers, year distribution sanity, share of papers with quartile or CORE rank assigned.
- Unit tests (`pytest`) for name matching, title normalisation, dedup, venue mapping, and the Indian-citation flags, using small fixture JSONs.

**CHECKPOINT 3:** Show me the QA report. Fix anything weak before moving on.

---

## 2. Downloadable outputs

Put everything in `deliverables/`:
- Official files, named exactly: `group9_data.csv` (the 14 spec columns in spec order: `group, institution, author, title, year, type, journal_name, issn, doi, citations, quartile, coauthor_institutes, cites_indian_inst, cited_by_indian_inst`), `citation_network.csv`, `authorship_network.csv`, `indian_connections.csv`.
- `group9_full_dataset.xlsx`, formatted (frozen headers, filters, column widths, number formats) with sheets: `README` (data dictionary, sources, collection date, method notes), `papers` (all extended columns), `faculty`, `faculty_paper_links`, `citation_edges`, `authorship_edges`, `indian_connections`, `citation_flow_by_year`, `findings` (one table per finding), `pre_joining_papers`, `preprints`, `qa_summary`. If any sheet would exceed Excel's row limit, keep it CSV-only and say so in README.
- `group9_deliverables.zip` containing all of the above.

---

## 3. Analysis

Precompute everything in Python (pandas, NetworkX, python-louvain or leidenalg, scikit-learn for NMI) and export JSON for the website. Each metric is computed per institution, per unit, and per year where meaningful.

### Required (from the instruction note)
- Publication trend 2016–2026 (total and per year, journal vs conference).
- Q1 fraction per institution, **and** CORE A*/A share of conference papers alongside it (journals are a minority of IIIT output, so Q1 alone misleads).
- Faculty h-index distribution, faculty list and performance table (papers, citations, top venue, h-index).
- Top 5 journals and top 5 conferences per institution; top 10 most-cited papers (title, venue, year, citations, DOI).
- Research area breakdown (OpenAlex field/subfield).
- Citation network: in-degree within our corpus, PageRank top 10, in-degree distribution, cross-institute flow.
- Authorship network: degree and betweenness centrality, Louvain/Leiden communities, cross-institution edges, hub authors bridging institutes.
- Citation flow: in-flow and out-flow with other Indian institutes, top 10 citing Indian institutes, citation impact ratio (in/out), year-wise flow 2016–2026.
- Connectivity map: every Indian partner, ranked by shared papers, co-authorship strength, cross-cluster links, topic Jaccard with partners.

### Central question: does the org chart shape who works with whom?
IIIT-H is organised by research centres, IIIT-D by departments. Run community detection on each institute's faculty co-authorship network, compare communities with official units using NMI, and compare modularity, average clustering, and the share of collaborations that cross a unit boundary between the two institutes. Recommendation logic: if clusters mirror units, cross-unit collaboration is rare, so joint PhD supervision or cross-unit seed grants are the lever; if not, the org chart is not the barrier.

### The seven findings (exactly these)
For each: compute, produce one headline number, one chart, one bolded recommendation, and the audience.

1. **The hidden glue** — scatter of betweenness vs degree for every faculty member. Flag high betweenness with ordinary degree (e.g. betweenness top 15%, degree below median; report thresholds). For each flagged person, remove them and record how much the largest connected component shrinks. *Action:* recognise and protect bridging roles in promotion and retention reviews. *Audience:* institute leadership.
2. **Weak points in each unit** — articulation points of each unit's internal co-authorship network; count per unit. *Action:* succession planning, co-supervision, or where to hire next. *Audience:* centre heads / department heads.
3. **How long new faculty take to fit in** — for faculty who joined 2016 or later, internal degree (co-authors within the institute) in years 1, 2, 3 after joining; share still at degree 0 after 3 years, by institute and unit. *Action:* mentoring and seed grants pairing new and established faculty. *Audience:* deans.
4. **Collaborations waiting to happen** — per-faculty topic sets; Jaccard similarity for every pair; list high-similarity pairs with no co-authored paper and no shared co-author, within each institute and across IIIT-H ↔ IIIT-D. *Action:* matchmaking list for seed grants, workshops, an IIIT-H–IIIT-D exchange. *Audience:* faculty and research office.
5. **Does bridging pay off?** — label each paper within-unit or cross-unit from its faculty authors' units; compare median citations against papers from the same year only. *Action:* evidence for (or against) funding interdisciplinary work. *Audience:* research office / funding committees.
6. **Concentration risk** — share of papers, citations, and collaboration links held by the top 10% of faculty, per institute, tracked 2016→2026 (add Gini as a secondary number). *Action:* support mid-career faculty if output rests on a few people. *Audience:* institute leadership.
7. **Who cites us but never works with us?** — rank Indian partner institutes by citations to us and by co-authored papers; flag high-citation, low-collaboration institutes; report the domestic share of our citations. *Action:* targets for MoUs and joint projects. *Audience:* outreach and partnerships office.

### Rigour
- Compare clustering, modularity, and cross-unit share against a **configuration-model null** (degree-preserving random graphs, at least 100 samples); report z-scores or "x times random".
- State every analytic choice (faculty-only nodes, preprint handling, large-paper down-weighting, h-index definition, quartile year rule) on a Methods tab.
- Never present a pattern from tiny groups without the group size next to it.

Also export the key charts as high-resolution PNGs to `report_figures/` for our ≤10-slide statistics report.

---

## 4. Website

A **static site** (no backend) so it can be emailed as a zip, opened locally, or hosted on GitHub Pages/Netlify. Suggested stack: Vite + React + TypeScript + Tailwind, ECharts or Plotly for charts, Cytoscape.js (or sigma.js for larger graphs) for networks, TanStack Table for tables. Data comes from the precomputed JSON. `npm run build` must produce a `dist/` that works from `file://` (relative base path) and from a web host. Add a "Download data" button linking to the deliverables zip.

### Design
Formal and sleek, like a research-office annual report: neutral background, generous whitespace, one consistent accent colour per institute used on every chart, a clean sans-serif (e.g. Inter), KPI cards with short labels, light and dark mode, fully responsive including phones. Every chart has a one-line caption saying what it shows and a small "method" tooltip. 2026 is visually marked as partial. No clutter, no default-looking templates.

### Global filters (persist across tabs, reflected in the URL)
Institution (IIIT-H / IIIT-D / both), unit (centre or department), year range slider, paper type (journal / conference / include preprints), faculty designation, and a faculty search box.

### Tabs
1. **Overview** — KPI cards (faculty, papers, citations, median h-index, Q1 share, CORE A*/A share, Indian partners), trend chart, IIIT-H vs IIIT-D side-by-side summary, three headline findings.
2. **Publications** — trend by year and type, top venues, most-cited top 10 with DOI links, full searchable paper table with CSV export.
3. **Faculty** — sortable, searchable performance table (name, unit, papers, citations, h-index both versions, top venue, degree, betweenness). Clicking a person opens a profile drawer: trend, venues, topics, co-authors, network position.
4. **Venues & Quality** — Q1–Q4 distribution, CORE A*/A/B/C breakdown, top journals and conferences per institute.
5. **Research Areas** — field and subfield shares, per-unit topic mix, treemap or sunburst.
6. **Citation Network** — interactive directed graph of the top-k papers by PageRank (k adjustable), nodes sized by in-degree and coloured by institute, PageRank top 10 table, in-degree distribution.
7. **Collaboration Network** — interactive faculty co-authorship graph, colour toggle (official unit / detected community / institute), node size by degree, hover highlights neighbours, search to focus. Include the **click-to-remove** mode for Finding 1: removing a node updates the largest-component size live.
8. **Centres vs Departments** — the central question: NMI, modularity, clustering, cross-unit share with null-model comparison, and a side-by-side unit-by-community matrix for each institute.
9. **Findings** — seven cards, each with the question, headline number, chart, bolded recommendation, and audience. Finding 4 gets a filterable **"Missed collaborations"** table; Finding 2 a per-unit articulation-point view; Finding 3 a new-joiner integration curve.
10. **Indian Connections** — citation in/out-flow by year, top 10 citing institutes, impact ratio, ranked partner list, cross-cluster link chart, partner topic Jaccard.
11. **Data & Methods** — downloads, data dictionary, sources, coverage and QA numbers (DBLP match rate, missing-field rates), and all analytic choices.

Every chart can be downloaded as PNG and every table as CSV. Include a checklist (in `README.md`) mapping each of the 11 required dashboard panels from the instruction note to where it lives on the site.

---

## 5. Repo layout

```
config.yaml            # institutes, years, email, thresholds, flags (preprints on/off, etc.)
pipeline/              # 01_roster … 06_qa, one script per step, each idempotent
analysis/              # required metrics, central question, findings 1–7, null models
data/raw/ data/cache/ data/external/ data/processed/
review/                # files for me to check by hand
qa/                    # qa_report.md
deliverables/          # official CSVs, xlsx, zip
report_figures/
site/                  # website source; site/dist = build
tests/
README.md              # how to run everything, choices made, panel checklist
```

## 6. How to work with me
- Plan first, then build step by step. Stop at the three checkpoints above.
- After each step, print a short summary: counts, coverage, and anything uncertain.
- If a source is down or blocked, try the next source and log it; do not quietly skip data.
- Finish with: the zip path, the site build path, how to host it, and the final QA numbers.