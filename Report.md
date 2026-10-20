# IIIT Hyderabad × IIIT Delhi — Research Mapping 2016–2026
### A Complete Report of the Citation Network Analysis Dashboard
**Prepared by:** DPCN Group 9 · **Data collected:** 2026-10-12 

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [How to Read This Report — Graph Terminology Explained](#2-how-to-read-this-report--graph-terminology-explained)
3. [Data Sources & Methodology](#3-data-sources--methodology)
4. [Overview Dashboard](#4-overview-dashboard)
5. [Publication Trends (2016–2026)](#5-publication-trends-20162026)
6. [Venue Quality Analysis](#6-venue-quality-analysis)
7. [Faculty Performance](#7-faculty-performance)
8. [Research Areas](#8-research-areas)
9. [Citation Network](#9-citation-network)
10. [Collaboration Network](#10-collaboration-network)
11. [Centres vs Departments — Does the Org Chart Shape Collaboration?](#11-centres-vs-departments--does-the-org-chart-shape-collaboration)
12. [Indian Connections](#12-indian-connections)
13. [Seven Actionable Findings](#13-seven-actionable-findings)
14. [Data Quality & Coverage](#14-data-quality--coverage)

---

## 1. Project Overview

This dashboard maps **every publication by IIIT Hyderabad (IIIT-H) and IIIT Delhi (IIIT-D) faculty from 2016 to 2026** (2026 is a partial year, data collected on 12 October 2026). It is a reproducible data pipeline that:

- Collected faculty rosters from official institute websites
- Retrieved publications from OpenAlex, DBLP, Crossref, Semantic Scholar, and IIIT-H's publications portal
- Built citation, co-authorship, and Indian-connection networks
- Performed a "centres vs departments" structural analysis
- Generated seven actionable findings aimed at institute leadership

### Headline Numbers at a Glance

| Metric | IIIT-H | IIIT-D |
|---|---|---|
| Core faculty (current) | 109 | 102 |
| Former core faculty (2016–2026) | 35 | 49 |
| Total papers (journal + conference) | 4,678 | 4,309 |
| Conference share of output | 61% | 54% |
| Q1 journal share (ranked journals) | ~54.5% | ~51.9% |
| CORE A\*/A conference share (ranked) | ~50.9% | ~56.2% |

> **Note on "Core faculty":** = faculty at Assistant Professor / Associate Professor / Full Professor level only. Adjunct, visiting, emeritus, and affiliate faculty are tracked but excluded from the main analysis. A paper with two faculty co-authors from the same institute is counted once per institute; a joint IIIT-H–IIIT-D paper is counted for both.

---

## 2. How to Read This Report — Graph Terminology Explained

This project uses several concepts from **network/graph theory**. Here is what each term means **in our specific context** of faculty co-authorship and paper citations.

### 2.1 Nodes and Edges

A **graph** is a set of objects (**nodes**) connected by relationships (**edges**).

- **In the co-authorship network:** Each *node* is a faculty member. An *edge* between two faculty members means they co-authored at least one paper together in the selected period.
- **In the citation network:** Each *node* is a paper. A *directed edge* from paper A to paper B means paper A cites paper B.

### 2.2 Degree

**Degree** = the number of direct connections a node has.

- **In the co-authorship network:** A faculty member's degree = how many *other faculty members* they have co-authored a paper with (within the same institute). A high degree means someone has collaborated widely.
- **In the citation network:** *In-degree* = how many papers cite this paper. A high in-degree means the paper is heavily cited from within the corpus.

### 2.3 Betweenness Centrality

**Betweenness** = the fraction of all shortest paths between pairs of nodes that pass *through* a given node.

- **In the co-authorship network:** A faculty member with high betweenness acts as a **bridge** — many of the shortest collaboration routes between pairs of colleagues pass through them. Even if they don't have many direct collaborators (low degree), their position in the network makes them structurally critical. **Removing them can disconnect large parts of the network.**
- Example: If A and D only know each other through B → C, then B and C have high betweenness.

### 2.4 PageRank

**PageRank** = an algorithm originally developed by Google that ranks nodes by how often a random walker visiting the graph would land on them. A page/paper is high-ranked if it is linked to by many other high-ranked pages/papers.

- **In the citation network:** A paper with high PageRank is not just cited many times; it is cited by papers that are themselves highly cited. It is the most **influential** paper within the IIIT corpus.

### 2.5 Connected Component / Largest Connected Component (LCC)

A **connected component** is a group of nodes where every member can reach every other member by following edges.

- **LCC = Largest Connected Component.** In the co-authorship network, the LCC is the biggest "collaboration cluster" — the set of faculty who are all connected to each other (directly or through chains of co-authors). If the LCC shrinks, the network has fragmented.
- **LCC Drop:** When a bridge faculty member is removed from the network, the LCC may shrink because some faculty who were only connected through that person lose their path to the rest. A drop from 98 to 92 means 6 faculty get isolated.

### 2.6 Articulation Point (Cut Vertex)

An **articulation point** is a single node whose removal *splits* its connected component into two or more disconnected parts.

- **In the co-authorship network (per unit):** If a faculty member is the *only link* between two sub-groups within their research centre/department, they are an articulation point. Their departure literally splits the unit's internal collaboration network.

### 2.7 Community Detection (Louvain Algorithm)

**Communities** are groups of nodes that are more densely connected to each other than to the rest of the graph.

- **Louvain algorithm** (seed 42) was used to detect communities. It works by iteratively moving nodes between groups to maximise a quality measure called **modularity** (see below).
- **In this project:** Communities in the co-authorship network are groups of faculty who mostly collaborate within the group. These may or may not align with official units (centres/departments).

### 2.8 Modularity

**Modularity** measures how well a network is divided into communities. Values range from –1 to 1; higher is better.

- A modularity of ~0.57 (IIIT-H detected communities) means the detected communities are well-separated — there is much more within-community collaboration than would be expected in a random network.
- A modularity of ~0.30 (IIIT-H official units) means official units are *less* well-suited as communities — suggesting collaboration crosses unit boundaries.

### 2.9 NMI (Normalised Mutual Information)

**NMI** measures how much two different ways of grouping the same set of nodes agree with each other. It ranges from 0 (completely different groupings) to 1 (identical groupings).

- **In this project:** NMI compares the *Louvain-detected communities* with the *official unit memberships* of faculty. An NMI of 0.57 (IIIT-H) means the collaboration-based communities partly mirror the official org chart. An NMI of 0.37 (IIIT-D) means less alignment.

### 2.10 Null Model (Degree-Preserving Rewiring)

A **null model** is a randomised version of the real network used as a baseline to tell us whether an observed pattern is due to chance.

- Here, the null model is created by **200 degree-preserving rewirings** (double-edge swaps): edges are randomly shuffled, but every faculty member keeps the same number of co-authors. Louvain is re-run on each randomised network.
- This tells us: "If collaboration partners were assigned randomly (keeping everyone's social circle size the same), what would clustering/modularity/cross-unit sharing look like?" Deviations from this baseline tell us something real about the structure.

### 2.11 Jaccard Similarity (Topic Jaccard)

**Jaccard** = |A ∩ B| / |A ∪ B|: the size of the overlap divided by the size of the union.

- **In this project:** Topic Jaccard between two faculty members = how many of their research topics overlap, divided by all topics between them. A Jaccard of 1.0 means they publish on exactly the same topics. Used in Finding 4 to identify faculty pairs who work on the same things but have never co-authored.

### 2.12 h-index

The **h-index** (Hirsch index) of a researcher = the largest number *h* such that *h* of their papers have each been cited at least *h* times.

- **Dataset h-index:** Computed only from papers in this dataset (2016–2026 main set), using OpenAlex citation counts. This measures recent/within-period impact.
- **Lifetime h-index:** From OpenAlex's summary statistics, taking the maximum over all known author IDs. This captures the person's full career impact.

---

## 3. Data Sources & Methodology

### 3.1 Sources

| Source | Used For |
|---|---|
| OpenAlex (API key) | Papers, authors, institutions, topics, citations, references |
| DBLP (SPARQL endpoint) | CS publication lists, journal/conference record types, ORCIDs |
| Crossref | DOIs, ISSNs, container titles, publication types |
| Semantic Scholar (keyless, best-effort) | Secondary citation counts |
| IIIT-H publications portal | Institute-reported records, CORE labels, journal flag |
| Official faculty pages (both institutes) | Roster, units, designations, homepages, joining years |
| Wayback Machine (CDX) | Former faculty — one snapshot per year 2016–2025 |
| Scimago SJR (2016–2025) | Journal quartiles (Q1–Q4) |
| CORE portal | Conference rankings (A\*, A, B, C) |

### 3.2 Key Analytic Choices

- **Who is included:** Core faculty only (Assistant/Associate/Full Professor). Papers count if the faculty member listed IIIT-H/IIIT-D on the paper, or if the paper falls on/after their joining year.
- **Preprints:** arXiv versions are merged into the published paper. arXiv-only works are excluded by default (toggleable in the UI).
- **Deduplication:** DOI first; then normalised title (fuzzy ratio ≥ 93) + year ±1 + a shared faculty member.
- **Co-authorship edge weight:** Σ 1/(n_authors − 1) across shared papers. Papers with > 25 authors are flagged (their per-paper weight ≤ 1/25).
- **Quartile assignment:** Scimago SJR best quartile across the journal's subject categories for the paper's publication year (nearest available year if missing).
- **CORE assignment:** CORE edition in force at publication time.
- **2026 is partial everywhere** (data through 12 October 2026).

---

## 4. Overview Dashboard

The Overview tab is the landing page of the website. It shows seven top-level KPIs and three headline findings.

### 4.1 Top-Level KPIs (combined, both institutes, 2016–2026)

| KPI | Value |
|---|---|
| Core faculty (in filter) | 211 (109 IIIT-H + 102 IIIT-D) |
| Total papers | ~8,987 (4,678 IIIT-H + 4,309 IIIT-D) |
| Q1 journal share (proxy) | ~54.5% IIIT-H / ~51.9% IIIT-D of ranked journal papers |
| CORE A\*/A conference share | ~50.9% IIIT-H / ~56.2% IIIT-D of ranked conference papers |

### 4.2 Side-by-Side Institution Comparison

| Metric | IIIT-H | IIIT-D |
|---|---|---|
| Faculty (core) | 109 | 102 |
| Papers (2016–2026) | 4,678 | 4,309 |
| Journal share | ~39% | ~46% |
| Q1 share (ranked journals) | ~54.5% | ~51.9% |
| CORE A\*/A (ranked conf.) | ~50.9% | ~56.2% |

**Key contrast:** IIIT-H publishes more at conferences (61% of output); IIIT-D has a higher journal share (46%) and publishes more in Q1 journals as a fraction of its output. Both are roughly comparable on CORE A\*/A conference quality. IIIT-D is organised by departments (CSE, ECE, CB, MATH, HCD, SSH), while IIIT-H is organised by research centres (CVIT, LTRC, CSTAR, SPCRC, etc.).

---

## 5. Publication Trends (2016–2026)

### 5.1 IIIT-H Annual Output

| Year | Conference | Journal | Total |
|---|---|---|---|
| 2016 | 187 | 131 | 318 |
| 2017 | 224 | 102 | 326 |
| 2018 | 240 | 132 | 372 |
| 2019 | 215 | 124 | 339 |
| 2020 | 226 | 149 | 375 |
| 2021 | 279 | 164 | 443 |
| 2022 | 293 | 214 | 507 |
| 2023 | 340 | 194 | 534 |
| 2024 | 301 | 232 | 533 |
| 2025 | 342 | 220 | 562 |
| 2026 *(partial)* | 217 | 152 | 369 |

**Trend:** IIIT-H output has grown ~77% from 2016 to 2025, with a particularly strong rise from 2020 onward. Journal output nearly doubled (131→220), reflecting growing recognition.

### 5.2 IIIT-D Annual Output

| Year | Conference | Journal | Total |
|---|---|---|---|
| 2016 | 203 | 87 | 290 |
| 2017 | 158 | 116 | 274 |
| 2018 | 235 | 138 | 373 |
| 2019 | 237 | 184 | 421 |
| 2020 | 234 | 200 | 434 |
| 2021 | 227 | 241 | 468 |
| 2022 | 207 | 243 | 450 |
| 2023 | 214 | 204 | 418 |
| 2024 | 257 | 197 | 454 |
| 2025 | 212 | 198 | 410 |
| 2026 *(partial)* | 128 | 189 | 317 |

**Trend:** IIIT-D's journal output overtook its conference output from 2021 onward — a significant structural shift. Total output peaked around 2020–2022 and has plateaued. IIIT-D had a higher conference count than IIIT-H in early years (2016–2017) but IIIT-H surpassed it from 2018 onward.

### 5.3 Top Most-Cited Papers (Combined Ranking)

| Rank | Title | Venue | Year | Institute | Citations |
|---|---|---|---|---|---|
| 1 | Cancer chemotherapy and beyond | Genes & Diseases | 2022 | IIIT-D | 1,826 |
| 2 | Age of Information: An Introduction and Survey | IEEE J. Selected Areas Comms. | 2021 | IIIT-D | 1,158 |
| 3 | Reference component analysis of single-cell transcriptomes | Nature Genetics | 2017 | IIIT-D | 1,075 |
| 4 | A Lip Sync Expert Is All You Need | ACM MM | 2020 | IIIT-H | 861 |
| 5 | Deep Learning for Hate Speech Detection in Tweets | WWW | 2017 | IIIT-H | 848 |
| 6 | The gut microbiome as a modulator of healthy ageing | Nature Reviews Gastroenterology | 2022 | IIIT-D | 800 |
| 7 | MVAE: Multimodal Variational Autoencoder for Fake News Detection | WWW | 2019 | IIIT-H | 798 |
| 8 | The Age of Information: Real-Time Status Updating | IEEE Trans. Information Theory | 2018 | IIIT-D | 666 |
| 9 | Ego4D: Around the World in 3,000 Hours of Egocentric Video | CVPR | 2022 | IIIT-H | 615 |
| 10 | VUzzer: Application-aware Evolutionary Fuzzing | NDSS | 2017 | IIIT-H | 584 |

IIIT-D's top papers are dominated by **computational biology and information theory**. IIIT-H's top papers are in **computer vision, NLP, and security**.

---

## 6. Venue Quality Analysis

### 6.1 Journal Quality (Scimago SJR Quartiles)

Journals are ranked Q1 (top 25% of their field) through Q4 (bottom 25%). The pipeline used an **OpenAlex-proxy quartile** (since Scimago files required a browser session that may not have been available at build time).

| Institute | Journal Papers | Ranked | Q1 | Q2 | Q3 | Q4 | Q1 share (of ranked) |
|---|---|---|---|---|---|---|---|
| IIIT-H | 1,814 | 1,692 | 922 | 526 | 142 | 102 | **54.5%** |
| IIIT-D | 1,997 | 1,989 | 1,034 | 562 | 253 | 140 | **51.9%** |

> **Note:** The Q1 share is computed **only over ranked papers**. Journals for which no quartile data exists are not included in the denominator. Both institutes have more than half of their ranked journal output in Q1.

**Top Journals:**
- **IIIT-H:** IEEE Access (73 papers, 3,860 citations), IEEE Internet of Things (69 papers), Physical Review A (49 papers), IEEE TVT (26 papers)
- **IIIT-D:** IEEE Access (57 papers), Scientific Reports (37 papers), PLOS ONE (27 papers), Briefings in Bioinformatics (18 papers)

### 6.2 Conference Quality (CORE Rankings)

CORE (Computing Research and Education) ranks conferences: **A\*** (top tier) > **A** > **B** > **C**.

| Institute | Conf. Papers | Ranked | A\* | A | B | C | A\*/A share (of ranked) |
|---|---|---|---|---|---|---|---|
| IIIT-H | 2,864 | 1,378 | 250 | 452 | 504 | 172 | **50.9%** |
| IIIT-D | 2,312 | 1,068 | 286 | 314 | 367 | 101 | **56.2%** |

> **Note:** Only ~48% (IIIT-H) and ~46% (IIIT-D) of conference papers have CORE rankings. The large number of unranked conferences is common across CS departments in India and globally.

**Top Conferences:**
- **IIIT-H:** ACL (83 papers), WACV (70 papers), ICPR (61 papers), ICVGIP (56 papers), SemEval (47 papers)
- **IIIT-D:** AAAI (66 papers), COMSNETS (59 papers), ICASSP (51 papers), ACL (42 papers), IEEE ANTS (41 papers)

### 6.3 Impact Factor Filter

The site allows filtering papers by venue Impact Factor (IF > 5 or IF > 10), where IF is the mean citations per paper in that venue within the dataset (not the official Clarivate JIF). This lets users identify high-impact subsets.

---

## 7. Faculty Performance

### 7.1 h-index Distribution

The site shows a histogram of the **dataset h-index** (computed only from 2016–2026 papers in the main set). Most faculty have a dataset h-index in the 2–10 range. The distribution is right-skewed — a few faculty have very high h-indices.

Each faculty member's **profile drawer** (click on their name) shows:
- Papers, Citations, h-index (dataset and lifetime)
- Degree and Betweenness centrality in the co-authorship network
- Papers-per-year bar chart
- Top venues published in
- Top research fields
- Faculty co-authors (ranked by joint papers)
- Network position: community, internal degree, internal betweenness

### 7.2 Faculty Table (Sortable Columns)

Every faculty member has the following metrics available:

| Column | Meaning |
|---|---|
| Name | Clickable — opens profile drawer |
| Inst. | IIIT-H or IIIT-D |
| Unit | Primary research centre (IIIT-H) or department (IIIT-D) |
| Designation | Assistant / Associate / Full Professor |
| Papers | Papers in main set (2016–2026) |
| Citations | Total OpenAlex citations at collection date |
| h (2016–26) | Dataset h-index |
| h (lifetime) | Lifetime h-index from OpenAlex |
| Top venue | Most frequent venue for this faculty member |
| Degree | Number of faculty co-authors (across both institutes) |
| Betweenness | Normalised betweenness on the unweighted faculty graph of both institutes |

> **Tip:** Sorting by **Betweenness** vs **Degree** reveals "hidden bridges" — faculty who are structurally critical without being the most prolific collaborators (see Finding 1).

---

## 8. Research Areas

### 8.1 Top Research Fields by Institute

Fields are from OpenAlex's classification (primary topic → subfield → field).

**IIIT-H top fields (by paper count):**
1. Computer Science (AI: 986, Computer Vision: 549, Networks: 478, Information Systems: 333)
2. Engineering (Electrical & Electronic: 276, Biomedical: 124, Control & Systems: 111)
3. Physics & Astronomy (Atomic/Molecular/Optics: 42, Nuclear/High Energy: 41)
4. Neuroscience (Cognitive Neuroscience: 94)
5. Social Sciences (Sociology & Political Science: 51)

**IIIT-D top fields (by paper count):**
1. Computer Science (AI: 647, Computer Vision: 370, Networks: 231, Computational Theory: 122)
2. Engineering (Electrical & Electronic: 649, Aerospace: 198, Computational Mechanics: 60)
3. Biochemistry, Genetics & Molecular Biology (Molecular Biology: 205, Cancer Research: 19)
4. Medicine (Cardiology: 33, Radiology: 29, Public Health: 27, Oncology: 14)
5. Mathematics (Algebra & Number Theory: 28, Applied Mathematics: 16)

**Key contrast:** IIIT-D has a much stronger **biomedical/life sciences** component (through its Computational Biology department — CB), which has no direct counterpart at IIIT-H. IIIT-H has stronger NLP/language technology output (LTRC centre). Both have strong AI and CV presence.

### 8.2 Treemap View

The site displays a treemap of each institute's field/subfield breakdown — rectangles sized by paper count. Clicking into a field-level rectangle drills down to subfields.

### 8.3 Topic Mix Per Unit (Heatmap)

A heatmap shows what fraction of each unit's papers fall into the institute's top 6 fields. This reveals:
- Which units are **specialised** (one dominant field) vs **interdisciplinary** (spread across fields)
- Which fields are claimed by multiple units (potential for intra-institute collaboration or competition)

---

## 9. Citation Network

### 9.1 What the Citation Network Is

This is a **directed graph** of citations between papers in the IIIT corpus itself — i.e., how often IIIT-H and IIIT-D papers cite each other's work.

- **Nodes:** Individual papers from the main set of both institutes
- **Directed edges:** Paper A → Paper B means A cites B
- **Node size** in the visualisation = **in-degree** (how many corpus papers cite this paper)
- **Arrows** point from citing paper to cited paper

### 9.2 In-Degree Distribution

The distribution of in-degrees follows a **power-law-like** shape (plotted on log-log scale): most papers are cited by 0 or 1 other corpus paper, while a small number of papers are cited by many. This is typical for citation networks.

### 9.3 PageRank Top 10

These are the **most influential papers within the IIIT corpus** — papers that are cited by many other highly-cited papers. The top-10 table is available on the Citation Network tab, showing title, venue, year, institute, and in-degree for each.

### 9.4 Cross-Institute Citation Flow

The citation flow table shows:
- How many IIIT-H papers cite IIIT-D papers
- How many IIIT-D papers cite IIIT-H papers
- Self-citations (IIIT-H citing IIIT-H, IIIT-D citing IIIT-D)

This answers: "Do the two institutes build on each other's work, or do they operate independently?"

### 9.5 Interactive Features

- **Slider:** Choose how many papers to display (top k by PageRank, from 50 to 600)
- **Play Timeline:** Animates the growth of the citation graph year by year (2016→2026), showing how the corpus built up over time
- **Hover:** Shows paper title, venue, year, and highlighted neighbours

---

## 10. Collaboration Network

### 10.1 What the Co-Authorship Network Is

This is an **undirected graph** of faculty who have written papers together.

- **Nodes:** Individual core faculty members (both institutes)
- **Edges:** Two faculty members are connected if they co-authored ≥ 1 paper in the selected year range
- **Node size** = degree (number of distinct faculty co-authors)
- **Edge weight** = Σ 1/(n_authors − 1) across shared papers (so a 2-author paper contributes 1.0, a 3-author paper contributes 0.5, etc.)

### 10.2 Colour Options

The network can be coloured by:
- **Institute** (IIIT-H in blue, IIIT-D in orange)
- **Official unit** (each centre/department gets its own colour)
- **Detected community** (Louvain algorithm groups — see Section 11)

### 10.3 IIIT-H ↔ IIIT-D Cross-Institute Collaboration

- **55 co-authored paper links** exist between the two institutes
- **21 distinct faculty pairs** have co-authored at least once

**Top hub bridgers (faculty with most cross-institute papers):**

| Faculty | Institute | Cross-Institute Papers |
|---|---|---|
| Ponnurangam Kumaraguru | IIIT-H (LTRC) | 31 |
| Rajiv Ratn Shah | IIIT-D (CSE) | 19 |
| Arun Balaji Buduru | IIIT-D (CSE) | 9 |
| Chetan Arora | IIIT-D (CSE) | 4 |
| Deva Priyakumar U | IIIT-H (CCNSB) | 4 |
| Jawahar C V | IIIT-H (CVIT) | 4 |

> **Note:** Ponnurangam Kumaraguru appears in both IIIT-H and IIIT-D data because he has been faculty at both institutions at different times during 2016–2026. His 31 cross-institute papers reflect this transitional period.

### 10.4 Most Central Faculty (by Betweenness)

The top 10 faculty by betweenness across both institutes' combined faculty graph are shown in the "Most central faculty" panel. These are the people who lie on the most shortest paths between other pairs of faculty — the critical connectors of the collaboration ecosystem.

### 10.5 Interactive Features

- **Click to remove:** Click on a node to remove it and see how the network changes — directly demonstrating Finding 1 (bridge importance)
- **Focus on a person:** Type a name to highlight them and their connections
- **Timeline animation:** See how the collaboration network grew year by year
- **Info panel:** Clicking a node shows that faculty's degree, betweenness, and community assignment

---

## 11. Centres vs Departments — Does the Org Chart Shape Collaboration?

This tab answers a fundamental question: **Does the way each institute is officially organised (IIIT-H by research centres, IIIT-D by departments) actually determine who collaborates with whom?**

### 11.1 Method

1. Build the within-institute faculty co-authorship network
2. Run the **Louvain community detection** algorithm to find natural collaboration clusters
3. Compare detected communities to official unit memberships using **NMI**
4. Compare observed **cross-unit collaboration** share to a **null model** (200 degree-preserving rewirings) to see if cross-unit links are rarer or more common than chance

### 11.2 Results: IIIT-H

| Metric | Value |
|---|---|
| Faculty with ≥1 internal co-author | 80 of 111 |
| Internal co-authorship edges | 189 |
| Official units (centres) | 19 |
| Detected Louvain communities | 9 |
| **NMI (communities vs units)** | **0.569** |
| Modularity of detected communities | 0.574 |
| Modularity of official units | 0.296 |
| Average clustering | 0.263 |
| Cross-unit share of co-authorship links | **70.4%** |
| Cross-unit share vs random | **0.75× random** (z = –13.3) |

**Interpretation for IIIT-H:**
- NMI of 0.569 means detected communities **largely mirror the official centres** — the org chart does predict collaboration to a meaningful degree.
- However, cross-unit collaboration (70.4%) is **25% rarer than chance** (z = –13.3, highly significant). The org chart acts as a partial barrier — faculty collaborate within their centre more than a random assignment would suggest.
- The Louvain algorithm finds **9 communities** from 19 centres, meaning several centres are naturally grouped together in practice.
- Clustering (0.263) is **2.98× higher than random** — strong local clustering (colleagues of colleagues are also colleagues).

### 11.3 Results: IIIT-D

| Metric | Value |
|---|---|
| Faculty with ≥1 internal co-author | 92 of 140 |
| Internal co-authorship edges | 172 |
| Official departments | 6 |
| Detected Louvain communities | 10 |
| **NMI (communities vs units)** | **0.371** |
| Modularity of detected communities | 0.669 |
| Modularity of official units | 0.401 |
| Average clustering | 0.257 |
| Cross-unit share of co-authorship links | **37.8%** |
| Cross-unit share vs random | **0.53× random** (z = –11.6) |

**Interpretation for IIIT-D:**
- NMI of 0.371 means communities **partly but not strongly follow** departments.
- Cross-unit collaboration (37.8%) is **47% rarer than chance** — IIIT-D's departments act as much stronger silos than IIIT-H's centres.
- The Louvain algorithm finds **10 communities** from only 6 departments — meaning some large departments (CSE especially) have strong internal sub-group structure.
- Clustering is **4.46× higher than random** — even stronger local clustering than IIIT-H.

### 11.4 The Community × Unit Matrix

A heatmap shows how faculty belonging to each official unit distribute across detected communities. A diagonal-heavy pattern (each unit mostly in one community) indicates that the org chart and collaboration structure align well. A scattered pattern indicates collaboration cuts across units.

### 11.5 What to Do With This

> **If clusters mirror units and cross-unit collaboration is rarer than chance, the org chart is the barrier: joint PhD supervision across units and cross-unit seed grants are the lever. If communities ignore the units, restructuring units will not change collaboration — invest in people and topics instead.**

For IIIT-H: the org chart matters somewhat (NMI = 0.57) and is a partial barrier. Cross-unit seed grants between adjacent centres could help.  
For IIIT-D: departments are stronger silos (cross-unit rate only 53% of random). Structural interventions (joint positions, cross-department seminars) are more warranted.

---

## 12. Indian Connections

### 12.1 What Is Tracked

This section tracks citation and co-authorship relationships between IIIT-H/IIIT-D and **other Indian institutions** (own institute excluded). Two types of connections are tracked:

- **Citations in (received):** Works by other Indian institutions that cite our papers
- **Citations out (given):** Our papers that cite works by other Indian institutions
- **Co-authored papers:** Papers with at least one author from another Indian institution

### 12.2 Impact Ratio

**Impact ratio = citations received from Indian institutes ÷ citations our papers give to Indian institutes**

A ratio > 1 means our work is cited more than we cite Indian peers — we are a net exporter of knowledge to India.

### 12.3 Indian Partner Breakdown by Type

Partner types tracked: IIT, NIT, IIIT, IISER, IISc/TIFR, CSIR, DAE, Central Universities, State Universities, Private, Other.

The bar chart shows co-authored papers with each type. IITs are typically the largest partners by joint paper count for both institutes.

### 12.4 Top Citing Indian Institutions

The top 10 Indian institutions (by citations to IIIT-H and IIIT-D papers respectively) are shown in separate bar charts. These reveal who builds on our research most heavily within India — often IITs and NITs with strong CS and engineering programs.

### 12.5 Indian Connections Faculty-to-Faculty Network

A separate faculty-to-faculty view shows which specific IIIT faculty have co-authored with which external Indian faculty, building a map of international Indian research connections.

---

## 13. Seven Actionable Findings

These are the core outputs of the analysis — each finding has a quantified headline, supporting data, a recommendation, and a target audience.

---

### Finding 1 · The Hidden Glue
**Question:** Who holds the collaboration network together without being among its most connected people?

**Headline:** Several faculty have **top-15% betweenness but ordinary degree** (not in the top quarter of most-connected people). These are the **hidden bridges**.

**Methodology:** For each institute, the within-institute unweighted co-authorship graph was built. Normalised betweenness centrality was computed for each faculty member. Faculty flagged = those with betweenness in the top 15% but degree ≤ the median (so they are not among the most active collaborators, yet many shortest paths run through them). Removing the top bridge cuts the Largest Connected Component by the stated number of faculty.

**Key examples from the data:**

| Name | Institute | Unit | Degree | Betweenness | LCC Before → After | Drop |
|---|---|---|---|---|---|---|
| Prasad Krishnan | IIIT-H | SPCRC | 5 | 0.0495 | 98 → 92 | **6 (5%)** |
| Kannan Srinathan | IIIT-H | CSTAR | 7 | 0.0391 | 98 → 96 | 1 |
| Radhika Mamidi | IIIT-H | LTRC | 7 | 0.0231 | 98 → 96 | 1 |
| Shaik Rehana | IIIT-H | LSI | 5 | 0.0251 | 98 → 97 | 0 |
| Ashish Kumar Pandey | IIIT-D | MATH | 4 | 0.0292 | 93 → 89 | **3 (3%)** |

*Betweenness is normalised on the within-institute unweighted faculty graph.*

**Recommendation:** Recognise and protect bridging roles in promotion and retention reviews — losing one of these people fragments collaboration more than losing a prolific author.

**Audience:** Institute leadership (Director, Dean of Faculty)

---

### Finding 2 · Weak Points in Each Unit
**Question:** Which units' internal collaboration hangs on single people?

**Headline:** Multiple **articulation points** exist across all units — single faculty whose departure would split their unit's co-authorship network into disconnected sub-groups.

**Methodology:** For each unit (using only faculty with that as their primary unit), the within-unit co-authorship graph was built. Articulation points were identified. The "cut off" count = faculty who would lose their connection to the rest of their unit's component.

**Recommendation:** Plan succession for these people — add co-supervision and pair them with a second faculty in each sub-area. Use the list to decide where to hire next.

**Audience:** Centre heads (IIIT-H) and department heads (IIIT-D)

---

### Finding 3 · How Long New Faculty Take to Fit In
**Question:** After three years, how many new faculty still have no co-author inside their institute?

**Headline:** A significant fraction of faculty who joined in 2016 or later still had **zero internal co-authors after 3 years**.

**Methodology:** Faculty who joined in 2016+ with a known joining year were tracked. Year 1 = joining year. Internal degree = cumulative distinct co-authors among same-institute core faculty by end of year 1, 2, and 3. Only faculty whose 3-year window ended by 2025 are counted (2026 is partial).

**Integration curve:** Both institutes show an upward trajectory year-over-year in median internal co-authors, but a notable fraction remain at zero after 3 years. The share at zero after 3 years is shown per institute (and per unit in the detailed table).

**Recommendation:** Pair each new hire with an established colleague through a mentoring scheme and a joint seed grant in year one.

**Audience:** Deans (Faculty Affairs / Research)

---

### Finding 4 · Collaborations Waiting to Happen
**Question:** Which pairs work on the same topics but have never written a paper together?

**Headline:** Many of the most topically similar faculty pairs (top 1%, ≥ 3 shared topics) **have never co-authored**. A subset span IIIT-H ↔ IIIT-D.

**Methodology:**
- Topic sets: OpenAlex topics appearing in ≥ 2 of a person's papers (all topics for people with < 5 papers).
- Only faculty with ≥ 3 topics are compared (smaller sets make Jaccard trivially high).
- Pairs already with a joint paper are excluded.
- **Tier 1** = no shared co-author at all (strict definition — truly disconnected in the network).
- **Tier 2** = already connected through a shared co-author (one introduction away).
- The table is filterable: all, cross-institute (IIIT-H ↔ IIIT-D), within IIIT-H, within IIIT-D.

> **Tip:** Tier 2 pairs (who share a co-author but haven't written together) are the **lowest-hanging fruit** for new collaborations — they already have a shared social connection.

**Recommendation:** Use the list as a matchmaking shortlist for seed grants, joint workshops and an IIIT-H–IIIT-D faculty exchange — start with pairs who already share a co-author.

**Audience:** Faculty and the research office

---

### Finding 5 · Does Bridging Pay Off?
**Question:** Are papers that cross unit boundaries cited more than within-unit papers from the same year?

**Headline:** A year-normalised citation ratio comparing **cross-unit papers vs within-unit papers** of the same publication year.

**Methodology:**
- Cross-unit = paper with faculty authors from ≥ 2 units (or both institutes). Within-unit = all authors from the same unit. Single-faculty papers excluded.
- Each paper's citations are divided by the **median citations of all papers from that year** (year-normalisation removes the effect of older papers having more time to accumulate citations).
- The ratio of pooled year-normalised median citations (cross-unit ÷ within-unit) is computed.
- Compared year-by-year (2016–2025, excluding 2026 partial).

**Recommendation (conditional on actual ratio):**
- If ratio > 1.05: "Fund interdisciplinary work — cross-unit papers earn more citations."
- If ratio < 0.95: "Do not assume interdisciplinary work pays in citations — fund it for other reasons."
- If near 1.0: "Citations are no reason for or against cross-unit funding — decide on strategic grounds."

**Audience:** Research office and funding committees

---

### Finding 6 · Concentration Risk
**Question:** How much of each institute's citation output rests on its top 10% of faculty?

**Headline:** The top 10% of faculty hold a disproportionate share of total citations — showing **output concentration risk**.

**Methodology:**
- Population = all core faculty of the institute (including those with zero papers).
- Top-10% share = output of the ⌈10% × faculty⌉ highest-output people ÷ total, computed per year.
- A **Gini coefficient** (0 = perfect equality, 1 = one person has everything) is also computed for papers and citations.

**Recommendation:** Support mid-career faculty (teaching relief, students, seed funds) so output does not depend on a few people.

**Audience:** Institute leadership

---

### Finding 7 · Who Cites Us But Never Works With Us?
**Question:** Which Indian institutes use our research heavily but have (almost) no joint papers with us?

**Headline:** Multiple Indian institutes are in the **top 10% by citations to us** but have ≤ 1 co-authored paper — they consume our research without collaborating.

**Methodology:**
- For each institute (IIIT-H and IIIT-D separately), rank all Indian partner institutes by citations received.
- Flag those in the top 10% by citations with ≤ 1 co-authored main-set paper.
- The domestic share of total citations = (citations from Indian institutes) / (all citations received).

**Output:** Two lists of "MoU targets" — Indian institutions that already build on our work and are therefore ready-made collaboration partners. The scatter plot (log-log: x = joint papers, y = citations to us) visually identifies top-left outliers — institutes that cite heavily but never co-author.

**Recommendation:** Target these institutes for MoUs, joint projects and visiting positions — they already build on our work.

**Audience:** Outreach and partnerships office

---

## 14. Data Quality & Coverage

The **Data & Methods tab** on the website lists all quality checks. Key metrics:

| Quality Check | Value | Interpretation |
|---|---|---|
| DBLP pooled recall | 76.2% | ~3 in 4 DBLP-listed CS papers were retrieved |
| Duplicate DOI rows | 0.0 | No DOI-based duplicates in final dataset |
| Duplicate title rows | 12 | 12 fuzzy-title near-duplicates remain (low) |
| Filled DOI | 95.6% | Strong DOI coverage |
| Filled CORE rank (conferences) | 49.9% | ~Half of conference papers have a CORE rank |
| Filled quartile proxy (journals) | 96.6% | Excellent journal quartile coverage via proxy |
| Filled citations | 99.7% | Almost all papers have a citation count |
| Filled co-author institutes | 91.4% | Strong co-authorship institution data |
| Filled research field | 97.2% | Strong OpenAlex field coverage |
| Faculty with zero papers | 30 | 30 core faculty had no retrievable main-set papers |
| CORE agreement with portal | 79.6% | Strong agreement between CORE ranks and IIIT-H portal |
| Self-loops in networks | 0 | No self-citations modelled |
| AB/BA duplicate edges | 0 | No undirected edge duplication |
| Own-partner rows in Indian network | 0 | Own institute properly excluded |
| Audit error rate | 2.1% | In a random spot-check, 2.1% of paper–faculty links were erroneous (below 5% threshold) |
| Fuzzy title threshold | 93 | Similarity score required to merge as duplicate |
| Overmerge filtered links | 2,054 | Links filtered to prevent incorrect cross-faculty merges |

> **Important:** **2026 is a partial year** in all analysis. Year-over-year comparisons in the findings use full years only (2016–2025). The 2026 bars/points are shown with hatching in charts.

> **Note on quartiles:** The quartile source shown in the dashboard is **"openalex_proxy"** rather than official Scimago SJR — meaning the proxy quartile (based on OpenAlex 2-year mean citedness within each journal's field) was used. This is noted prominently in all Q1 KPIs.

---

## Summary Table — All 11 Required Dashboard Panels

| # | Required Panel | Tab on Website |
|---|---|---|
| 1 | Publication trend 2016–2026 | Overview, Publications |
| 2 | Q1 fraction per institution (with CORE A\*/A share) | Venues & Quality, Overview |
| 3 | Faculty h-index distribution | Faculty |
| 4 | Faculty list and performance table | Faculty |
| 5 | Top 5 journals and conferences per institution | Publications, Venues & Quality |
| 6 | Top 10 most-cited papers | Publications |
| 7 | Research area breakdown | Research Areas |
| 8 | Citation network (in-degree, PageRank, flow) | Citation Network |
| 9 | Authorship network (degree, betweenness, communities, bridges) | Collaboration Network, Centres vs Departments |
| 10 | Citation flow with Indian institutes | Indian Connections |
| 11 | Connectivity map of Indian partners | Indian Connections, Findings (7) |

---

