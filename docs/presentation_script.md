# Presentation script: IIIT-H × IIIT-D Research Map (DPCN Group 9)

**How to use this:** lines in plain text are what you say. Lines in *[brackets]* are what you click or point at. Total run time is about 20–25 minutes; the sections marked *(optional)* can be skipped if time is short. Numbers come from the build of 13 Oct 2026 (data collected 12 Oct 2026). A final rebuild that merges a few dozen duplicate papers may shift paper counts by under 1%. Re-check the Overview tiles before presenting.

*[Before you start: open `site/dist/index.html` in a browser. It is a single file and works offline. Keep the Overview tab open.]*

---

## 1. Opening (1 minute)

*[Overview tab, filter bar on "Both".]*

Good morning, sir. We are Group 9, and our two institutes are IIIT Hyderabad and IIIT Delhi.

We set out to map every paper published by the faculty of both institutes from 2016 to 2026. From those papers we built three networks: who cites whom, who writes with whom, and how the two institutes connect with the rest of India. We then used simple network measures — degree, betweenness, connected components, communities and citation counts — to answer one central question and produce seven findings. Every finding ends in a concrete recommendation and names who should act on it.

Everything you will see is in this one web page. It works offline, it works on a phone, and every chart and table can be downloaded.

---

## 2. The data, and why you can trust it (3 minutes)

*[Stay on Overview. Point at the KPI tiles.]*

The first question for any project like this is whether the data is right, so let me start there.

**Who counts as faculty.** We took 295 core faculty, meaning Assistant, Associate and Full Professors: 109 current and 35 former at IIIT-H, and 102 current and 49 former at IIIT-D. We scraped the official faculty pages of both institutes. We then checked our count against an outside source, the faculty tables each institute submits to NIRF. For IIIT-D the match is exact: NIRF lists 99 regular professor-rank faculty, and so do we. IIIT-H's detailed NIRF tables are not publicly accessible, so there we used the archived copies of the IIIT-H faculty page, one per year since 2015. Those show the faculty growing steadily from 63 to 95 to today's 109, which tells us we did not miss pages.

Former faculty matter too. Someone who left in 2019 still wrote papers here in 2016, 2017 and 2018. We recovered former faculty from those archived yearly pages, and for IIIT-D we confirmed their joining and leaving dates from NIRF.

**Which papers count.** We combined five sources: OpenAlex, DBLP, Crossref, Semantic Scholar, and IIIT-H's own publication portal. DBLP is important because it covers computer-science conferences far better than general databases. After merging and removing duplicates, we have **8,985 journal and conference papers**. A paper counts for a faculty member if it lists IIIT-H or IIIT-D as their affiliation, or if it was published after they joined. Papers from before they joined are kept separately and do not inflate the numbers.

**Getting authors right.** This was the hardest part. Databases split one person into several profiles, and they merge different people who share a name. A common name like "Anuj Kumar" can pull in dozens of strangers. We matched people using ORCID, DBLP and affiliations. We then rejected any profile whose research topics did not fit the person's verified work. 97% of current IIIT-D faculty and 94% of current IIIT-H faculty are matched. Where a name was too ambiguous to resolve, we left it unmatched rather than guess.

**How we checked it.**
- We compared our paper counts with DBLP for every faculty member: the median agreement is 87%.
- We checked 50 random papers against the publisher's own record: the error rate is 2%.
- We recomputed one headline number for each of the seven findings from scratch, using only the Excel file we are handing in: all seven matched.

*[Point at the "Publications per year" chart.]*

This chart shows output by year. Blue is IIIT-H and orange is IIIT-D; those two colours mean the same institute on every chart. IIIT-H grew from 321 papers in 2016 to 566 in 2025, and IIIT-D from 293 to 410. The hatched bars at the end are 2026, which is only a partial year, so they are lower. We mark 2026 as partial everywhere on the site.

---

## 3. The filter bar (1 minute)

*[Point at the filter bar.]*

The filter bar at the top applies to every tab: institute, centre or department, year range, paper type, designation, and a faculty-name search. The current view is saved in the page address, so any filtered view can be shared as a link.

*[Set Institute = IIIT-H, then IIIT-D, then Both. Read the "Papers" tile each time.]*

The numbers add up. IIIT-H has 4,710 papers and IIIT-D has 4,329. 54 papers are joint between the two institutes, and 4,710 plus 4,329 minus 54 gives exactly the 8,985 we see for both.

*[Set Institute back to Both.]*

---

## 4. Tab tour (5 minutes)

### Publications

*[Click "Publications".]*

This tab breaks output down by journal and conference. Conferences are 57% of all papers: 61% at IIIT-H and 54% at IIIT-D. That is what we would expect for computer-science-heavy institutes.

*[Scroll to "Top conferences".]*

IIIT-H's most frequent conference venues are ACL, WACV, ICPR, ICVGIP and IROS. IIIT-D's are AAAI, COMSNETS, ICASSP, ACL and IEEE ANTS.

*[Scroll to "Ten most-cited papers".]*

These are the most-cited papers, with DOI links. At IIIT-H the top three are a lip-sync generation paper at ACM Multimedia with 861 citations, a hate-speech detection paper at WWW with 848, and a fake-news detection paper at WWW with 798.

*[Scroll to the full table.]*

Below that is every paper in a searchable, sortable table, which can be exported as a CSV.

### Faculty

*[Click "Faculty".]*

This is the faculty performance table: papers, citations, two h-indexes, top venue, and network position. We report two h-indexes on purpose. One uses only papers from 2016 to 2026 in our dataset; the other is the lifetime value from OpenAlex. Mixing them up is a common mistake.

*[Click "Citations" to sort. Then click a name, for example Jawahar C V.]*

Clicking a name opens a profile panel: papers per year, top venues, research fields, and their faculty co-authors.

*[Close the panel.]*

### Venues & Quality

*[Click "Venues & Quality".]*

This tab is about publication quality. On IIIT campuses, looking only at the share of Q1 journal papers is misleading, because journals are less than half of the output. So we always show the conference measure next to it. Among ranked conference papers, the share at CORE A* or A is **51% at IIIT-H and 56% at IIIT-D**.

One caveat to state openly. The official journal quartiles come from Scimago, and Scimago blocks automated downloads. The quartiles you see here are labelled as a proxy. We computed them from the journal's citation impact compared with established journals in the same field. The official Scimago numbers can be dropped in with one command.

### Research Areas

*[Click "Research Areas".]*

This tab shows research fields. Computer science is 57% of IIIT-H papers but 43% of IIIT-D papers. IIIT-D has more engineering and more biology and medicine, which comes from its Computational Biology department.

*[Scroll to the treemap and the unit heatmap.]*

The treemap breaks fields into subfields, and the heatmap shows each centre or department's topic mix.

### Citation Network

*[Click "Citation Network". Move the slider from 200 up to 600 and back.]*

This is the citation network inside our corpus: 8,724 papers with 10,854 citations among them. The slider shows the top papers by PageRank. Node size is the number of citations from inside the corpus, and colour is the institute.

*[Point at the tight blue cluster.]*

The dense blue cluster is IIIT-H's security and authentication group. The top PageRank paper is "SEAP: Secure and efficient authentication protocol for NFC applications" from 2016.

*[Scroll to "Cross-institute citation flow".]*

The two institutes rarely cite each other. IIIT-H cites IIIT-D 84 times and IIIT-D cites IIIT-H 91 times, against more than 5,000 internal citations at each.

### Collaboration Network

*[Click "Collaboration Network".]*

This is the faculty co-authorship network. Each dot is a faculty member, and a line means at least one paper together. Node size is the number of co-authors.

*[Click "official unit", then "detected community", then back to "institute".]*

We can colour it by institute, by official centre or department, or by communities that an algorithm detected in the network. Comparing the last two is our central question.

Between the two institutes there are only 21 faculty pairs who have written together. The main bridges are Ponnurangam Kumaraguru, who moved from IIIT-D to IIIT-H, Rajiv Ratn Shah, and Arun Balaji Buduru.

*[Turn "Click-to-remove" on. Click one well-connected node and read the "Largest component" counter. Then click Restore.]*

This is the click-to-remove mode. Removing a person updates the size of the largest connected group live, which is the idea behind our first finding.

---

## 5. The central question: does the org chart shape who works with whom? (3 minutes)

*[Click "Centres vs Departments".]*

This is our central question. The two institutes are organised differently: IIIT-H by research centres, of which there are 19, and IIIT-D by six departments. Does that structure decide who works with whom?

We did three things.

First, we let a community-detection algorithm find groups in each institute's co-authorship network, without telling it anything about the official units. We then measured how closely those groups match the official units, using normalised mutual information, where 0 means unrelated and 1 means identical.

*[Point at the two big numbers.]*

The answer is 0.54 at IIIT-H and 0.35 at IIIT-D. Who-works-with-whom follows IIIT-H's centres moderately well, and IIIT-D's departments less so.

Second, we compared each network with random networks that keep every person's number of co-authors but scramble who those co-authors are. We used 200 such random networks per institute.

*[Point at the "Observed vs random" chart.]*

Against that random baseline, collaborations that cross unit boundaries are far rarer than chance at both institutes. At IIIT-H, 70% of collaboration links cross a centre boundary, but in the random networks it would be 93%. That is a z-score of about minus 14. At IIIT-D, 38% cross a department boundary against 71% at random, a z-score of about minus 12. Both networks are also three to four times more clustered than random.

*[Scroll to the two unit-by-community matrices.]*

These matrices show the detail. Each row is an official unit and each column a detected community. A diagonal-looking pattern means communities follow the units.

**Our answer:** yes, the org chart shapes collaboration at both institutes, and more strongly at IIIT-H. **Recommendation:** since collaboration across units is the exception, the lever is structural. Joint PhD supervision across centres or departments, and seed grants that require two units, would change this. **Audience:** institute leadership and the academic council.

This result is robust. It does not change if we remove papers with more than 25 authors, or if we add preprints.

---

## 6. The seven findings (8 minutes)

*[Click "Findings". Use the chips at the top to jump between findings.]*

Each finding has the same structure: a question, one headline number, one chart, a bold recommendation, and who should act on it.

### Finding 1: The hidden glue

*[Click chip "1 · The hidden glue".]*

**Question:** who holds the collaboration network together without being among its most connected people?

We measured betweenness, which is how often a person lies on the shortest path between two colleagues. We then looked for people in the top 15% for betweenness whose number of co-authors is ordinary, meaning not in the top quarter.

**Number:** 7 people. Six are at IIIT-H, from SPCRC, CSTAR, CQST, CCNSB, LSI and LTRC, and one is at IIIT-D, in Mathematics. Removing Prasad Krishnan alone cuts IIIT-H's largest connected group from 98 to 92, so 5 colleagues lose their path to everyone else.

One honest detail: with the stricter rule of "below-median degree", nobody qualifies. At both institutes, the bridges are also reasonably well connected. We report both thresholds on the card.

*[Point at the scatter plot. Flagged people have a dark outline.]*

**Recommendation: recognise and protect bridging roles in promotion and retention reviews.** Losing one of these people fragments collaboration more than losing a more prolific author. **Audience:** institute leadership.

*[Stage note: Prof. Chittaranjan Hens (CCNSB) appears in this list and in Finding 2. If it comes up, say: "the method is purely structural — it identifies network position, not individual performance."]*

### Finding 2: Weak points in each unit

*[Click chip "2 · Weak points in each unit".]*

**Question:** which units' internal collaboration hangs on single people?

We found the articulation points of each unit's internal network. These are people whose departure would split their unit's collaboration network into disconnected pieces.

**Number:** 32 single points of failure across all units. IIIT-D CSE has the most, 9 of its 52 faculty. IIIT-D ECE has 5, and IIIT-H CSTAR and CCNSB have 3 each. Group sizes are shown next to every unit, so a small unit is never over-read.

**Recommendation: plan succession for these people.** Add co-supervision, pair each one with a second faculty member in their sub-area, and use the list to decide where to hire next. **Audience:** centre heads at IIIT-H and department heads at IIIT-D.

### Finding 3: How long new faculty take to fit in

*[Click chip "3 · How long new faculty take to fit in".]*

**Question:** after three years, how many new faculty still have no co-author inside their own institute?

We took faculty who joined in 2016 or later. Joining years come from NIRF for IIIT-D and from the archived faculty pages for IIIT-H. We counted how many distinct colleagues they had co-authored with by the end of years one, two and three.

**Number:** **65% at IIIT-D**, out of 96 new faculty, and **44% at IIIT-H**, out of 57, still had zero internal co-authors after three years. The median new faculty member has no internal co-author even by year three at IIIT-D, and one by year three at IIIT-H. By unit it is highest in IIIT-D Mathematics, at 13 of 14 people, and IIIT-H Human Sciences, at 7 of 9.

**Recommendation: pair each new hire with an established colleague in year one, through a formal mentoring scheme and a joint seed grant.** **Audience:** the Deans of Faculty and of Research.

### Finding 4: Collaborations waiting to happen

*[Click chip "4 · Collaborations waiting to happen". Scroll to the "Missed collaborations" table and click "cross-institute".]*

**Question:** which pairs of faculty work on the same topics but have never written a paper together?

For every faculty member we built a set of research topics from their papers, and compared every pair using Jaccard similarity. We kept the top 1% most similar pairs with at least three topics in common, and removed pairs who have already written together.

**Number:** **47 high-overlap pairs have never co-authored, and 34 of them span IIIT-H and IIIT-D.** Three pairs are complete strangers, with no shared co-author either. Examples are Sumit Darak (IIIT-D) and Ubaidulla P (IIIT-H), both in wireless communication and cognitive radio, and Arun Balaji Buduru (IIIT-D) and Suryakanth Gangashetty (IIIT-H), both in speech and emotion recognition. The other 44 are one introduction away: they already share a co-author. For example, Tanmoy Chakraborty and Ponnurangam Kumaraguru share 13 topics.

**Recommendation: use this table as a matchmaking shortlist** for seed grants, joint workshops and an IIIT-H–IIIT-D faculty exchange, starting with the pairs who already share a co-author. **Audience:** faculty and the research offices.

### Finding 5: Does bridging pay off?

*[Click chip "5 · Does bridging pay off?".]*

**Question:** are papers that cross unit boundaries cited more than papers within one unit?

Each paper with two or more of our faculty is labelled within-unit or cross-unit. We compared citations only between papers from the same year, because older papers have had more time to collect citations.

**Number:** cross-unit papers receive about **0.8 times** the citations of same-year within-unit papers. That is 353 cross-unit papers against 582 within-unit papers, and cross-unit papers were ahead in only 1 of 10 full years.

**Recommendation:** interdisciplinary work does not earn extra citations here. **Fund it for strategic reasons, such as new areas and capability, not for expected citation gains, and track its outcomes.** **Audience:** the research office and funding committees.

### Finding 6: Concentration risk

*[Click chip "6 · Concentration risk".]*

**Question:** how much of each institute's output rests on its top 10% of faculty?

**Number:** the top 10% of faculty hold **68% of all citations at IIIT-H and 66% at IIIT-D**, and 45% and 49% of the papers. For each year we counted only faculty who were actually in post that year, because both institutes roughly doubled in size. The share fell slightly over the decade at IIIT-H, from 71% in 2016 to 64% in 2025, and stayed near 65% at IIIT-D. The Gini coefficient for citations is about 0.77 to 0.79.

**Recommendation: support mid-career faculty** with teaching relief, students and seed funds, so that the institute's research profile does not rest on a few people. **Audience:** institute leadership.

### Finding 7: Who cites us but never works with us?

*[Click chip "7 · Who cites us but never works with us?". Point at the top-left of the scatter plot.]*

**Question:** which Indian institutes use our research heavily but almost never co-author with us?

**Number:** **45 institutes for IIIT-H and 57 for IIIT-D** are in the top 10% of Indian institutions by citations to us, yet have at most one joint paper. For IIIT-H these include NIT Patna, Symbiosis, Nirma University and Anna University. For IIIT-D they include Savitribai Phule Pune University, NIT Warangal and Anna University. Domestic citations, meaning citations from other Indian institutions, are 24% of IIIT-H's citations and 19% of IIIT-D's.

**Recommendation: target these institutes for MoUs, joint projects and visiting positions**, because they already build on our work. **Audience:** the outreach and partnerships office.

---

## 7. Indian Connections (2 minutes, optional)

*[Click "Indian Connections".]*

This tab is about connections to the rest of India. Both institutes are net exporters of knowledge within India. IIIT-H receives 26,215 citations from other Indian institutions and gives 19,092, an impact ratio of 1.37. IIIT-D receives 19,616 and gives 14,573, a ratio of 1.35.

*[Point at the line chart.]*

This chart shows the flow by year. Solid lines are citations received and lighter lines with open circles are citations given. The drop at the end is 2026, the partial year.

*[Scroll to "Top 10 citing Indian institutions".]*

IIIT-D's biggest Indian citer is IIT Delhi, which is also its biggest co-author with 280 joint papers. That is a healthy two-way relationship. IIIT-H's biggest citers are Graphic Era, VIT and Thapar.

*[Scroll to "Joint papers by partner type".]*

This chart groups partners by type: IITs, NITs, IIITs, IISERs, CSIR labs, central and state universities, and private universities. It shows which part of the Indian system each institute works with most.

---

## 8. Rigour and honesty (1 minute)

*[Click "Data & Methods".]*

Everything we decided is written down on this tab:
- the paper and faculty rules;
- how duplicates are removed;
- that co-authorship networks include faculty only;
- that very large team papers are down-weighted;
- that communities come from the Louvain method with a fixed seed;
- the 200-sample random-network comparison;
- both h-index definitions;
- that 2026 is partial.

Every group-level number is shown with its group size. We reran the key results without large-team papers and with preprints included, and no finding changes direction.

We are also open about the limits:
- Journal quartiles are a labelled proxy until the Scimago files are added.
- About 50% of conference papers have a CORE rank, because many venues are simply not in CORE.
- Former faculty are matched at about 76%, because many are humanities faculty or left early in the period.
- Where a name was too ambiguous to resolve, we left it unmatched rather than guess.

---

## 9. Close (1 minute)

*[Click "Download data" in the header.]*

The "Download data" button gives one zip file containing:
- the four official files, with exactly the columns in the instruction note;
- a 12-sheet Excel workbook with papers, faculty, links, networks, every finding's table, pre-joining papers, preprints and QA;
- the full QA report.

The whole pipeline reruns with one command, `make all`, and every web request is cached so it is reproducible.

To summarise:
- The org chart shapes collaboration at both institutes, more so at IIIT-H.
- New faculty integrate slowly.
- Output is concentrated in a few people.
- There are 34 ready-made IIIT-H–IIIT-D pairings waiting to happen.

Each of these has a concrete owner and action.

Thank you, sir. We are happy to take questions.

---

## Likely questions and answers

**Q: Why not use Google Scholar?**
Scholar forbids automated scraping and blocks it. We used open sources that allow it: OpenAlex, DBLP, Crossref and Semantic Scholar. OpenAlex citation counts are lower than Scholar's; that is expected, not an error.

**Q: How do you know a paper belongs to the right person?**
We used ORCID, DBLP and affiliation evidence, then a topic-consistency check that rejects profiles unlike the person's verified work. The checks against DBLP and the 50-paper publisher audit are on the Data & Methods tab.

**Q: Why is NMI higher for IIIT-H if it has more units?**
NMI corrects for the number of groups. IIIT-H's centres are topical, such as vision, language and robotics, so topic communities naturally line up with them. IIIT-D's departments are broader, and research groups cut across them. IIIT-D itself says it "has not maintained strong department boundaries".

**Q: Isn't 0.8× in Finding 5 just because cross-unit papers are newer?**
No. We only compare papers from the same year, and the result holds in 9 of 10 full years.

**Q: What counts as a paper being "ours"?**
The faculty member lists IIIT-H or IIIT-D on the paper, or the paper is from after they joined. Earlier unaffiliated papers are in a separate sheet and excluded.

**Q: Why are the 2026 bars low?**
2026 is a partial year, up to the collection date of 12 October 2026, and is marked as such everywhere.

**Q: Why is the top-cited IIIT-D paper a cancer review?**
It is co-authored by Jaspreet Kaur Dhanjal of IIIT-D's Computational Biology department. The paper itself lists IIIT-D as her affiliation (*Genes & Diseases*, 2022, DOI 10.1016/j.gendis.2022.02.007). IIIT-D's biology department is why its top-cited list is more biomedical than IIIT-H's.

**Q: Can this be updated next year?**
Yes. `make all` reruns everything from the cache and fetches only what is new.
