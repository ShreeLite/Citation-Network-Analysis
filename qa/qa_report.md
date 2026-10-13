# QA report — Group 9 (IIIT-H + IIIT-D)

Collection date: 2026-10-12  
Main set: 8,985 papers, 10,249 faculty–paper links, 265 of 295 core faculty with ≥1 paper.

## 1. DBLP spot check

Faculty with a DBLP PID: 232 of 295 core. Pooled recall of DBLP journal+conference records (2016–2026) in our main set: **76.2%**. Median per-person recall: 87.2%. Median ours/DBLP count ratio: 1.08 (>1 is expected: we also hold non-CS venues DBLP does not index).

Worst 20 by recall:

| name                     | institution   |   dblp_count |   our_count |   dblp_found_in_ours |   dblp_recall |
|:-------------------------|:--------------|-------------:|------------:|---------------------:|--------------:|
| Kuldeep Ramchandra Kurte | IIIT-H        |           26 |           1 |                    0 |         0     |
| K.K. Biswas              | IIIT-D        |           18 |           0 |                    0 |         0     |
| Sachit Butail            | IIIT-D        |           14 |           4 |                    0 |         0     |
| Pragma Kar               | IIIT-D        |           11 |           2 |                    0 |         0     |
| Sandeep Sen              | IIIT-D        |            8 |           0 |                    0 |         0     |
| Astrid Kiehn             | IIIT-D        |            2 |           0 |                    0 |         0     |
| N. Arul Murugan          | IIIT-D        |            2 |          47 |                    0 |         0     |
| Tarini Shankar Ghosh     | IIIT-D        |            1 |          34 |                    0 |         0     |
| Puneet Goyal             | IIIT-D        |           47 |           1 |                    1 |         0.021 |
| Shubhajit Roy Chowdhury  | IIIT-H        |           36 |           8 |                    2 |         0.056 |
| Rahul Mishra             | IIIT-H        |           10 |           9 |                    1 |         0.1   |
| Tanmay Bhowmik           | IIIT-H        |           43 |          17 |                    5 |         0.116 |
| Moumita Patra            | IIIT-H        |           32 |           4 |                    4 |         0.125 |
| Sandeep Kumar Shukla     | IIIT-H        |          129 |          42 |                   18 |         0.14  |
| Priyesh Shukla           | IIIT-H        |           13 |           3 |                    2 |         0.154 |
| Antony Thomas            | IIIT-H        |           19 |           7 |                    3 |         0.158 |
| Tanmoy Kundu             | IIIT-D        |            5 |           1 |                    1 |         0.2   |
| Rahul Shrestha           | IIIT-H        |           55 |          15 |                   12 |         0.218 |
| Sudipta Banerjee         | IIIT-H        |           26 |           8 |                    6 |         0.231 |
| Arti Yardi               | IIIT-H        |           13 |           7 |                    3 |         0.231 |

## 2. Random audit sample

50 random papers with all fields: `review/audit_sample.csv` (fill `verified` = Y/N).

## 3. Duplicate check

Papers sharing a DOI: 0. Papers with identical normalised title and year: 98.

Listed in `qa/possible_duplicates.csv` (many are legitimate conference + journal versions with different DOIs).

## 4. Field coverage

| field                   | filled   | missing   |    n |
|:------------------------|:---------|:----------|-----:|
| doi                     | 95.6%    | 4.4%      | 8985 |
| issn (journals)         | 96.7%    | 3.3%      | 3832 |
| quartile (journals)     | 0.0%     | 100.0%    | 3832 |
| CORE rank (conferences) | 49.8%    | 50.2%     | 5153 |
| journal_name            | 100.0%   | 0.0%      | 8985 |
| citations               | 99.5%    | 0.5%      | 8985 |
| coauthor_institutes     | 91.2%    | 8.8%      | 8985 |
| field                   | 96.9%    | 3.1%      | 8985 |
| citations_s2            | 92.4%    | 7.6%      | 8985 |

## 5. Faculty with zero or suspiciously many papers

Core faculty with zero main-set papers: 30: Acushla Saraswat (IIIT-D, no unit), Ashok K. Mittal (IIIT-D, no unit), Ashwin Srinivasan (IIIT-D, CSE), Astrid Kiehn (IIIT-D, CSE), Deepak Prince (IIIT-D, SSH), K.K. Biswas (IIIT-D, no unit), Nikhil Gupta (IIIT-D, CSE), Prahllad Deb (IIIT-D, MATH), Pydi Ganga Mamba Bahubalindruni (IIIT-D, ECE), Raj Ayyar (IIIT-D, no unit), Sandeep Sen (IIIT-D, CSE), Shireen Mirza (IIIT-D, SSH), Somitra Kr. Sanadhya (IIIT-D, CSE), Timothy Scott Moyers Jr (IIIT-D, HCD), Abdul Rehaman Moughal Shahi (IIIT-H, no unit), Acharya Nand Kishore (IIIT-H, no unit), Angarika Rakshit (IIIT-H, HSRC), Ashwin Jayanti (IIIT-H, HSRC), Don Wallace Freeman Dcruz (IIIT-H, no unit), Kaul C. N. (IIIT-H, no unit), Khaliq Parkar (IIIT-H, HSRC), Kishore S Prahallad (IIIT-H, LTRC), Rakesh Kiran Chand Thumaty (IIIT-H, LSI), Rambabu Kalla (IIIT-H, no unit), Rao P. R. K (IIIT-H, no unit), Semparithi Aravindan (IIIT-H, CCNSB), Vijaya Sankara Rao P. (IIIT-H, no unit), Indrani De Parker (IIIT-D, no unit), Manohar Khushalani (IIIT-D, no unit), Samaresh Chatterji (IIIT-D, no unit)

Top 1% by paper count (check for over-merged profiles): Rajiv Ratn Shah (247), Ashok Kumar Das (499), Jawahar C V (295)

## 6. Year distribution (2026 is partial)

|   year |   conference |   journal |
|-------:|-------------:|----------:|
|   2016 |          392 |       218 |
|   2017 |          380 |       223 |
|   2018 |          478 |       272 |
|   2019 |          448 |       307 |
|   2020 |          459 |       352 |
|   2021 |          504 |       405 |
|   2022 |          493 |       454 |
|   2023 |          549 |       401 |
|   2024 |          554 |       433 |
|   2025 |          554 |       421 |
|   2026 |          342 |       346 |

## 7. Merge diagnostics

Source records: {'openalex': 20533, 'dblp': 12401, 'iiith_portal': 4440}. Fuzzy title threshold used: 93.

|   threshold |    tp |   fp |   fn |   precision |   recall |
|------------:|------:|-----:|-----:|------------:|---------:|
|          85 | 14950 |  631 |  361 |      0.9595 |   0.9764 |
|          88 | 14948 |  553 |  363 |      0.9643 |   0.9763 |
|          90 | 14946 |  515 |  365 |      0.9667 |   0.9762 |
|          92 | 14945 |  484 |  366 |      0.9686 |   0.9761 |
|          93 | 14940 |  477 |  371 |      0.9691 |   0.9758 |
|          95 | 14933 |  447 |  378 |      0.9709 |   0.9753 |
|          97 | 14898 |  422 |  413 |      0.9725 |   0.973  |

Links filtered as over-merged OpenAlex profiles: 2100 (`review/overmerge_filtered.csv`). Pre-joining links: 4493. After-leaving links: 1834.

CORE rank agreement with the IIIT-H portal's own labels: 79.6% of 798 papers where both exist.

## 8. cited_by_indian_inst spot check (per-paper group_by vs batched pipeline)

| paper_id    |   pipeline_n_institutions |   group_by_n_institutions_incl_non_IN | pipeline_flag   |
|:------------|--------------------------:|--------------------------------------:|:----------------|
| W4396840805 |                         1 |                                     2 | True            |
| W2917201317 |                         1 |                                     1 | True            |
| W4312897680 |                         1 |                                     1 | True            |
| W4210953093 |                         3 |                                     5 | True            |
| W4388776132 |                         1 |                                     1 | True            |
| W4213372913 |                         1 |                                     1 | True            |
| W4312056336 |                         4 |                                     4 | True            |
| W4388291711 |                         6 |                                    10 | True            |
| W4404137175 |                         3 |                                     4 | True            |
| W4296184108 |                        13 |                                    20 | True            |
| W2772394551 |                         1 |                                     2 | True            |
| W2477348760 |                         6 |                                    17 | True            |
| W4308303341 |                         1 |                                     1 | True            |
| W2895547158 |                         9 |                                    14 | True            |
| W2894278110 |                         7 |                                    11 | True            |
| W4237467126 |                         3 |                                     8 | True            |
| W2982594830 |                         5 |                                    13 | True            |
| W4403688595 |                         9 |                                   199 | True            |
| W4388748466 |                         4 |                                     6 | True            |
| W2403443505 |                         7 |                                    19 | True            |

## 9. Papers per year (smoothness)

- Years dipping below 70% of their neighbours' mean: none (2026 excluded: partial).

## 10. Most prolific faculty (max papers in one year)

| Faculty | Year | Papers that year | Total 2016–26 |
|---|---|---|---|
| Ashok Kumar Das | 2024 | 70 ⚠ > 40 | 499 |
| Rajiv Ratn Shah | 2020 | 46 ⚠ > 40 | 247 |
| Tanmoy Chakraborty | 2021 | 36 | 199 |
| Jawahar C V | 2022 | 35 | 295 |
| Richa Singh | 2019 | 33 | 131 |

## 11. Journal vs conference

- conference 57.4%, journal 42.6% (OK: conference-heavy as expected for CS institutes).
- Per institute: IIIT-D: conf 54%; IIIT-H: conf 61%

## 12. Duplicates incl. arXiv beside published

- arXiv-only records whose title equals a published main-set paper: 48 (arXiv version > 2 years before publication). They are treated as the published paper: excluded from the preprint toggle, the preprints sheet and every count, so no paper appears twice.

## 13. Ranking coverage and top venues

- Journal papers with a Scimago SJR quartile: 0.0% (Scimago files not available — Cloudflare blocks automated download); with the labelled OpenAlex proxy quartile: 96.1%.
- Conference papers with a CORE rank: 49.8%.

**IIIT-D top 20 venues:** AAAI (66), COMSNETS (61), ACCESS (57), ICASSP (51), ACL (42), IEEEANTS (41), SR (37), INTERSPEECH (37), WACV (33), BIGMM (33), CHI (32), IJCNN (31), VLSID (31), CVPR (28), ICPR (27), Plos One (27), ICIP (27), EMNLP (27), MWSCAS (23), APMC (23)

**IIIT-H top 20 venues:** ACL (89), ACCESS (73), WACV (70), IOT (69), ICPR (64), ICVGIP (56), PRA (49), SEMEVAL (47), IROS (47), INTERSPEECH (41), CVPR (39), ISCAS (39), ATAL (39), ICDAR (39), ICRA (37), AAAI (37), ISIT (36), MWSCAS (36), ICON-NLP (36), IJCNN (34)

## 14. Ten most-cited papers

| Title | Venue | Year | Citations |
|---|---|---|---|
| Cancer chemotherapy and beyond: Current status, drug candidates, associated risks and prog | Genes & Diseases | 2022 | 1826 |
| Age of Information: An Introduction and Survey | IEEE Journal on Selected Areas in Communications | 2021 | 1158 |
| Reference component analysis of single-cell transcriptomes elucidates cellular heterogenei | Nature Genetics | 2017 | 1075 |
| A Lip Sync Expert Is All You Need for Speech to Lip Generation In the Wild | ACM MM | 2020 | 861 |
| Deep Learning for Hate Speech Detection in Tweets | WWW | 2017 | 848 |
| The gut microbiome as a modulator of healthy ageing | Nature Reviews Gastroenterology & Hepatology | 2022 | 800 |
| MVAE: Multimodal Variational Autoencoder for Fake News Detection | WWW | 2019 | 798 |
| The Age of Information: Real-Time Status Updating by Multiple Sources | T-IT | 2018 | 666 |
| Ego4D: Around the World in 3,000 Hours of Egocentric Video | CVPR | 2022 | 615 |
| VUzzer: Application-aware Evolutionary Fuzzing | NDSS | 2017 | 584 |

OpenAlex counts run below Google Scholar's; that is expected.

## 15. Indian-citation flags

- cites_indian_inst TRUE: 55.9%; cited_by_indian_inst TRUE: 48.7% (OK: strictly between 0% and 100%).

Hand-check (direct per-paper OpenAlex query):

| paper       | title                                                        | flag   | own_only_case   |   citing_groups_excl_own |
|:------------|:-------------------------------------------------------------|:-------|:----------------|-------------------------:|
| W3103227824 | Modelling hydrological responses under climate change using  | True   | False           |                        7 |
| W4317789861 | DeConDFFuse : Predicting drug–drug interaction using joint d | True   | False           |                        1 |
| W4396840805 | Coprime networks of the composite numbers: Pseudo-randomness | True   | False           |                        2 |
| W2898274421 | Biometrics-Based Privacy-Preserving User Authentication Sche | True   | False           |                      139 |
| W2512816756 | Evaluation of “Autotune” calibration against manual calibrat | False  | True            |                        0 |

A paper cited by Indian works only from its own institute must be FALSE — the own-only case above is FALSE when its row shows flag = False.

## 16. Network files

- Citation edges whose source paper is in the papers table: 100.0%
- Self-loops: citation 0, authorship 0
- A–B and B–A duplicates (same paper) in authorship edges: 0
- Partner rows where an institute is its own partner: 0

## 17. Official file format

- Columns exactly as spec, in order: True
- group = 9 on every row: True
- Rows: 10,249; written as UTF-8 with BOM so Excel shows accented/Indic characters correctly (621 cells contain non-ASCII text).
- Files: group9_data.csv ✓, citation_network.csv ✓, authorship_network.csv ✓, indian_connections.csv ✓

## 18. Audit sample vs publisher record (Crossref)

- 50 random papers; 46 have a publisher DOI and were checked. Error rate: 2.2% (solid (< 5%)).
- Title mismatches 0, year mismatches 1, type mismatches 0 — details in `qa/audit_publisher_check.csv`.
