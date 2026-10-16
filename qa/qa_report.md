# QA report — Group 9 (IIIT-H + IIIT-D)

Collection date: 2026-10-12  
Main set: 8,934 papers, 10,187 faculty–paper links, 265 of 295 core faculty with ≥1 paper.

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
| N. Arul Murugan          | IIIT-D        |            2 |          46 |                    0 |         0     |
| Tarini Shankar Ghosh     | IIIT-D        |            1 |          33 |                    0 |         0     |
| Puneet Goyal             | IIIT-D        |           47 |           1 |                    1 |         0.021 |
| Shubhajit Roy Chowdhury  | IIIT-H        |           36 |           8 |                    2 |         0.056 |
| Rahul Mishra             | IIIT-H        |           10 |           9 |                    1 |         0.1   |
| Tanmay Bhowmik           | IIIT-H        |           43 |          17 |                    5 |         0.116 |
| Moumita Patra            | IIIT-H        |           32 |           4 |                    4 |         0.125 |
| Sandeep Kumar Shukla     | IIIT-H        |          129 |          42 |                   18 |         0.14  |
| Priyesh Shukla           | IIIT-H        |           13 |           3 |                    2 |         0.154 |
| Antony Thomas            | IIIT-H        |           19 |           6 |                    3 |         0.158 |
| Tanmoy Kundu             | IIIT-D        |            5 |           1 |                    1 |         0.2   |
| Rahul Shrestha           | IIIT-H        |           55 |          15 |                   12 |         0.218 |
| Sudipta Banerjee         | IIIT-H        |           26 |           8 |                    6 |         0.231 |
| Hrishikesh B. Acharya    | IIIT-D        |           21 |           5 |                    5 |         0.238 |

## 2. Random audit sample

50 random papers with all fields: `review/audit_sample.csv` (fill `verified` = Y/N).

## 3. Duplicate check

Papers sharing a DOI: 0. Papers with identical normalised title and year: 12.

Listed in `qa/possible_duplicates.csv` (many are legitimate conference + journal versions with different DOIs).

## 4. Field coverage

| field                   | filled   | missing   |    n |
|:------------------------|:---------|:----------|-----:|
| doi                     | 95.6%    | 4.4%      | 8934 |
| issn (journals)         | 97.1%    | 2.9%      | 3799 |
| quartile (journals)     | 0.0%     | 100.0%    | 3799 |
| CORE rank (conferences) | 49.9%    | 50.1%     | 5135 |
| journal_name            | 100.0%   | 0.0%      | 8934 |
| citations               | 99.7%    | 0.3%      | 8934 |
| coauthor_institutes     | 91.4%    | 8.6%      | 8934 |
| field                   | 97.2%    | 2.8%      | 8934 |
| citations_s2            | 92.7%    | 7.3%      | 8934 |

## 5. Faculty with zero or suspiciously many papers

Core faculty with zero main-set papers: 30: Acushla Saraswat (IIIT-D, no unit), Ashok K. Mittal (IIIT-D, no unit), Ashwin Srinivasan (IIIT-D, CSE), Astrid Kiehn (IIIT-D, CSE), Deepak Prince (IIIT-D, SSH), K.K. Biswas (IIIT-D, no unit), Nikhil Gupta (IIIT-D, CSE), Prahllad Deb (IIIT-D, MATH), Pydi Ganga Mamba Bahubalindruni (IIIT-D, ECE), Raj Ayyar (IIIT-D, no unit), Sandeep Sen (IIIT-D, CSE), Shireen Mirza (IIIT-D, SSH), Somitra Kr. Sanadhya (IIIT-D, CSE), Timothy Scott Moyers Jr (IIIT-D, HCD), Abdul Rehaman Moughal Shahi (IIIT-H, no unit), Acharya Nand Kishore (IIIT-H, no unit), Angarika Rakshit (IIIT-H, HSRC), Ashwin Jayanti (IIIT-H, HSRC), Don Wallace Freeman Dcruz (IIIT-H, no unit), Kaul C. N. (IIIT-H, no unit), Khaliq Parkar (IIIT-H, HSRC), Kishore S Prahallad (IIIT-H, LTRC), Rakesh Kiran Chand Thumaty (IIIT-H, LSI), Rambabu Kalla (IIIT-H, no unit), Rao P. R. K (IIIT-H, no unit), Semparithi Aravindan (IIIT-H, CCNSB), Vijaya Sankara Rao P. (IIIT-H, no unit), Indrani De Parker (IIIT-D, no unit), Manohar Khushalani (IIIT-D, no unit), Samaresh Chatterji (IIIT-D, no unit)

Top 1% by paper count (check for over-merged profiles): Rajiv Ratn Shah (247), Ashok Kumar Das (496), Jawahar C V (295)

## 6. Year distribution (2026 is partial)

|   year |   conference |   journal |
|-------:|-------------:|----------:|
|   2016 |          387 |       217 |
|   2017 |          379 |       218 |
|   2018 |          475 |       270 |
|   2019 |          446 |       305 |
|   2020 |          458 |       349 |
|   2021 |          501 |       404 |
|   2022 |          492 |       452 |
|   2023 |          548 |       397 |
|   2024 |          554 |       428 |
|   2025 |          553 |       418 |
|   2026 |          342 |       341 |

## 7. Merge diagnostics

Source records: {'openalex': 20530, 'dblp': 12401, 'iiith_portal': 4440}. Fuzzy title threshold used: 93.

|   threshold |    tp |   fp |   fn |   precision |   recall |
|------------:|------:|-----:|-----:|------------:|---------:|
|          85 | 14872 |  509 |  363 |      0.9669 |   0.9762 |
|          88 | 14870 |  431 |  365 |      0.9718 |   0.976  |
|          90 | 14868 |  396 |  367 |      0.9741 |   0.9759 |
|          92 | 14867 |  368 |  368 |      0.9758 |   0.9758 |
|          93 | 14862 |  361 |  373 |      0.9763 |   0.9755 |
|          95 | 14855 |  335 |  380 |      0.9779 |   0.9751 |
|          97 | 14820 |  313 |  415 |      0.9793 |   0.9728 |

Links filtered as over-merged OpenAlex profiles: 2054 (`review/overmerge_filtered.csv`). Pre-joining links: 4360. After-leaving links: 1828.

CORE rank agreement with the IIIT-H portal's own labels: 79.7% of 801 papers where both exist.

## 8. cited_by_indian_inst spot check (per-paper group_by vs batched pipeline)

| paper_id    |   pipeline_n_institutions |   group_by_n_institutions_incl_non_IN | pipeline_flag   |
|:------------|--------------------------:|--------------------------------------:|:----------------|
| W3206172186 |                         1 |                                     1 | True            |
| W2805485249 |                         3 |                                     4 | True            |
| W2988256164 |                         1 |                                     4 | True            |
| W3128918010 |                         7 |                                     7 | True            |
| W4392745439 |                         2 |                                     2 | True            |
| W2994071599 |                        81 |                                    98 | True            |
| W2938241428 |                        17 |                                    20 | True            |
| W3164128501 |                         3 |                                     4 | True            |
| W4283026634 |                         7 |                                    10 | True            |
| W3170818115 |                        14 |                                    16 | True            |
| W2513440619 |                        23 |                                    38 | True            |
| W2587018232 |                         1 |                                     1 | True            |
| W3215062209 |                         1 |                                     3 | True            |
| W3011712033 |                         1 |                                     1 | True            |
| W2782804866 |                         2 |                                     2 | True            |
| W4403758994 |                         3 |                                     6 | True            |
| W2761942122 |                         8 |                                    19 | True            |
| W2508499722 |                         2 |                                     2 | True            |
| W4414110805 |                         2 |                                     4 | True            |
| W2775741307 |                         1 |                                     1 | True            |

## 9. Papers per year (smoothness)

- Years dipping below 70% of their neighbours' mean: none (2026 excluded: partial).

## 10. Most prolific faculty (max papers in one year)

| Faculty | Year | Papers that year | Total 2016–26 |
|---|---|---|---|
| Ashok Kumar Das | 2024 | 70 ⚠ > 40 | 496 |
| Rajiv Ratn Shah | 2020 | 46 ⚠ > 40 | 247 |
| Tanmoy Chakraborty | 2021 | 36 | 198 |
| Jawahar C V | 2025 | 35 | 295 |
| Angshul Majumdar | 2016 | 33 | 218 |

## 11. Journal vs conference

- conference 57.5%, journal 42.5% (OK: conference-heavy as expected for CS institutes).
- Per institute: IIIT-D: conf 54%; IIIT-H: conf 61%

## 12. Duplicates incl. arXiv beside published

- arXiv-only records whose title equals a published main-set paper: 22 (arXiv version > 2 years before publication). They are treated as the published paper: excluded from the preprint toggle, the preprints sheet and every count, so no paper appears twice.

## 13. Ranking coverage and top venues

- Journal papers with a Scimago SJR quartile: 0.0% (Scimago files not available — Cloudflare blocks automated download); with the labelled OpenAlex proxy quartile: 96.6%.
- Conference papers with a CORE rank: 49.9%.

**IIIT-D top 20 venues:** AAAI (66), COMSNETS (59), ACCESS (57), ICASSP (51), ACL (42), IEEEANTS (41), SR (37), INTERSPEECH (37), WACV (33), BIGMM (33), CHI (32), IJCNN (31), VLSID (31), CVPR (28), ICPR (27), Plos One (27), ICIP (27), EMNLP (27), MWSCAS (23), APMC (23)

**IIIT-H top 20 venues:** ACL (89), ACCESS (73), WACV (70), IOT (69), ICPR (63), ICVGIP (56), PRA (49), SEMEVAL (47), IROS (47), INTERSPEECH (41), CVPR (39), ISCAS (39), ATAL (39), ICDAR (39), ICRA (37), AAAI (37), ISIT (36), MWSCAS (36), ICON-NLP (36), IJCNN (34)

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

- cites_indian_inst TRUE: 56.1%; cited_by_indian_inst TRUE: 48.9% (OK: strictly between 0% and 100%).

Hand-check (direct per-paper OpenAlex query):

| paper       | title                                                        | flag   | own_only_case   |   citing_groups_excl_own |
|:------------|:-------------------------------------------------------------|:-------|:----------------|-------------------------:|
| W4290794768 | Dynamic matching in campus placements: The benefits and affo | True   | False           |                        1 |
| W2469171359 | Limits imposed by nonlinear coupling on rotation sensitivity | True   | False           |                        1 |
| W4408352334 | Psycholinguistic Features Predict Word Duration in Hindi Rea | True   | False           |                        1 |
| W4401413973 | Anticipate & Act: Integrating LLMs and Classical Planning fo | True   | False           |                        2 |
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
- Rows: 10,187; written as UTF-8 with BOM so Excel shows accented/Indic characters correctly (621 cells contain non-ASCII text).
- Files: group9_data.csv ✓, citation_network.csv ✓, authorship_network.csv ✓, indian_connections.csv ✓

## 18. Audit sample vs publisher record (Crossref)

- 50 random papers; 47 have a publisher DOI and were checked. Error rate: 2.1% (solid (< 5%)).
- Title mismatches 0, year mismatches 0, type mismatches 1 — details in `qa/audit_publisher_check.csv`.
