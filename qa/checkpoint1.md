# Checkpoint 1 — roster sanity checks

## 1. Count vs NIRF

- **IIIT-H**: 109 current core faculty scraped (148 listed incl. adjunct/visiting/etc.). NIRF 2025 'faculty members entered': 141 (NIRF also counts lecturers and contractual/visiting staff).
- **IIIT-D**: 99 current core faculty scraped (165 listed incl. adjunct/visiting/etc.). NIRF 2025 'faculty members entered': 184 (NIRF also counts lecturers and contractual/visiting staff).
- **IIIT-D like-for-like**: NIRF 2026 lists 99 current regular professor-rank faculty; roster has 99 → gap 0.0% (OK).
  - in NIRF but not on site as core: ['Anand Srivastava', 'Angshu Das', 'Bijendra Nath Jain', 'D K Sharma', 'Debidas Kundu', 'Pankaj Jalote', 'Subhajit Ghosechowdhury', 'Vinish Kathuria']
  - on site as core but not in NIRF: ['Anuj Kumar', 'Debarka Sengupta', 'Paro Mishra', 'Rahul Mohanani', 'Sachchidanand Prasad', 'Sandeep Sen', 'Sanjit Krishnan Kaul', 'Sukanta Nandi']

Independent like-for-like trajectory — professor-rank faculty listed on each institute's own archived faculty page (one Wayback snapshot per year):

|   year |   IIIT-D | IIIT-H   |
|-------:|---------:|:---------|
|   2015 |       38 | 64.0     |
|   2016 |       38 | 62.0     |
|   2017 |       49 | 65.0     |
|   2018 |       56 | —        |
|   2019 |       59 | 64.0     |
|   2020 |       75 | 70.0     |
|   2021 |       84 | 72.0     |
|   2022 |       85 | 85.0     |
|   2023 |       83 | 91.0     |
|   2024 |       88 | 96.0     |
|   2025 |       97 | —        |

Today: IIIT-H 109, IIIT-D 99. Steady growth to today's counts means no pages were missed; the IIIT-H gap to the NIRF total is NIRF counting research scientists, lecturers, visiting and contractual staff.

## 2. Wrong people

- Designation/name containing non-faculty words (scholar|engineer|officer|student|post[- ]?doc|manager|staff|intern|research associate|project associate|fellow\b|assistant registrar|librarian|coordinator): 2
  - IIIT-H: Khushboo Agarwal — Ramanujan Faculty Fellow Ph.D (IIT Bombay) [other]
  - IIIT-H: Radhika Mamidi — Associate Professor, Dean of Students Affairs (DOSA), Ph.D (University of Hyderabad) [core]
- Exact duplicate names within an institute: 0
- Near-duplicate names ("Dr." variants etc.): none

- Designation classes: IIIT-D: {'core': 136, 'adjunct': 51, 'visiting': 12, 'professor_of_practice': 2, 'emeritus': 1, 'lecturer': 2}; IIIT-H: {'core': 140, 'emeritus': 8, 'research_staff': 3, 'visiting': 8, 'distinguished': 7, 'adjunct': 20, 'other': 1, 'affiliate': 1, 'professor_of_practice': 3, 'lecturer': 1}

## 3. Units

- **IIIT-D** (6 units): CSE 29, ECE 24, SSH 17, MATH 13, CB 11, HCD 5
  - with a secondary unit: 15; small units (< 5 core faculty): []
- **IIIT-H** (19 units): HSRC 12, CCNSB 11, CSTAR 11, LTRC 10, SPCRC 9, CVIT 7, SERC 6, CVEST 6, RRC 5, CSL 5, EERC 5, LSI 5, CQST 4, DSAC 4, MLL 3, CSG 3, BMRC 1, KCIS 1, CMC 1
  - with a secondary unit: 9; small units (< 5 core faculty): ['CQST', 'DSAC', 'MLL', 'CSG', 'BMRC', 'KCIS', 'CMC']
- Each person appears once: yes

## 4. Spot check of known names

| Institute | Name | Found as | Unit | Designation | Status | Joining year (source) | Check |
|---|---|---|---|---|---|---|---|
| IIIT-H | P J Narayanan | Narayanan P J | CVIT  | Professor | current |  () | ✓ |
| IIIT-H | C V Jawahar | Jawahar C V | CVIT  | Professor | current |  () | ✓ |
| IIIT-H | K Madhava Krishna | K Madhava Krishna | RRC  | Professor | current |  () | ✓ |
| IIIT-H | Kamalakar Karlapalem | Kamalakar Karlapalem | DSAC  | Professor | current | 2000.0 (stated_homepage) | ✓ |
| IIIT-H | Ponnurangam Kumaraguru | Ponnurangam Kumaraguru | LTRC  | Professor | current | 2019.0 (wayback_first_listed) | ✓ |
| IIIT-H | Dipti Misra Sharma | Dipti Misra Sharma | LTRC  | Professor Emeritus, Ph.D (Delhi University) | current |  () | ✓ |
| IIIT-H | Vineet Gandhi | Vineet Gandhi | CVIT  | Associate Professor | current | 2016.0 (wayback_first_listed) | ✓ |
| IIIT-D | Anubha Gupta | Anubha Gupta | ECE + CSE | Professor | current | 2013 (nirf_dcs) | ✓ |
| IIIT-D | Vikram Goyal | Vikram Goyal | CSE  | Professor | current | 2009 (nirf_dcs) | ✓ |
| IIIT-D | Gajendra Pal Singh Raghava | G.P.S. Raghava | CB  | Professor | current | 2017 (nirf_dcs) | ✓ |
| IIIT-D | Pankaj Jalote | Pankaj Jalote | CSE  | Emeritus Professor | current | 2008 (nirf_dcs) | ✓ |
| IIIT-D | Debarka Sengupta | Debarka Sengupta | CB + CSE | Professor | current | 2017 (nirf_dcs) | ✓ |

Mismatches: 0 of 12 (OK).

## 5. Joining years

- Outside [founding year, 2026]: 0 
- Source among current core faculty: nirf_dcs 95 (46%), wayback_first_listed 53 (25%), missing 51 (25%), stated (homepage/CV/profile) 9 (4%)
- Missing exact year but bounded: listed in the earliest snapshot (joined ≤ that year, i.e. before 2016): 30; absent from all snapshots (joined after the last one; refined from the first institute-affiliated paper in step 2): 21
- Homepages rarely state a joining year (4%), so official NIRF dates (IIIT-D) and first appearance on the archived faculty list (IIIT-H) carry most of the load; both are documented per person in `joining_year_evidence`.

## 6. Former faculty

- 83 former-faculty rows: wayback 70, wayback+nirf 10, nirf 3
  - IIIT-D: Acushla Saraswat — Assistant Professor — listed 2020-2022 in 3 yearly snapshots as 'Lecturer'; e.g. https://web.archive.org/web/20220116102135/https://iiitd.ac.i
  - IIIT-D: Alexander Fell — Assistant Professor — listed 2015-2017 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170129130937/http://
  - IIIT-D: Amarjeet Singh — Assistant Professor — listed 2015-2016 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20160311155551/https:/
  - IIIT-D: Apala Guha — Assistant Professor — listed 2015-2016 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20160311155551/https:/
  - IIIT-D: Ashok K. Mittal — Professor — listed 2017-2018 in 2 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20180108001805/http://www.iiitd.
  - IIIT-D: Ashwin Srinivasan — Professor — listed 2015-2015 in 1 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20150107034827/http://www.iiitd.
  - IIIT-D: Astrid Kiehn — Associate Professor — listed 2015-2015 in 1 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20150107034827/http://
  - IIIT-D: Chetan Arora — Assistant Professor — listed 2015-2018 in 4 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20180108001805/http://
  - IIIT-D: Donghoon Chang — Associate Professor — listed 2015-2022 in 7 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20220116102135/https:/
  - IIIT-D: G.S. Visweswaran — Professor — listed 2017-2021 in 4 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20210128161655/https://www.iiitd
  - IIIT-D: Grace Eden — Assistant Professor — listed 2020-2022 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20220116102135/https:/
  - IIIT-D: Hrishikesh B. Acharya — Assistant Professor — listed 2015-2016 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20160311155551/https:/
  - IIIT-D: Indrani De Parker — Professor — NIRF DCS 2022-2023; left 2022.0
  - IIIT-D: Jatin Batra — Assistant Professor — listed 2021-2021 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20210128161655/https:/
  - IIIT-D: Juhi Ranjan — Assistant Professor — listed 2018-2018 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20180108001805/http://
  - IIIT-D: K.K. Biswas — Professor — listed 2017-2017 in 1 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20170129130937/http://iiitd.ac.i
  - IIIT-D: Manohar Khushalani — Professor — NIRF DCS 2023-2023; left 2022.0
  - IIIT-D: Mayank Vatsa — Associate Professor — listed 2015-2019 in 5 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20190107093734/https:/
  - IIIT-D: Mohammad S. Hashmi — Professor — listed 2015-2022 in 6 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20220116102135/https://iiitd.ac.
  - IIIT-D: Payel C Mukherjee — Professor — listed 2020-2020 in 1 yearly snapshots as 'Lecturer'; e.g. https://web.archive.org/web/20200512203635/https://iiitd.ac.i
  - IIIT-D: Puneet Goyal — Assistant Professor — listed 2016-2016 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20160311155551/https:/
  - IIIT-D: Pydi Ganga Mamba Bahubalindruni — Assistant Professor — listed 2016-2018 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20180108001805/http://
  - IIIT-D: Raj Ayyar — Assistant Professor — listed 2017-2019 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20190107093734/https:/
  - IIIT-D: Richa Singh — Associate Professor — listed 2015-2019 in 5 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20190107093734/https:/
  - IIIT-D: Sachit Butail — Assistant Professor — listed 2015-2015 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20150107034827/http://
  - IIIT-D: Samaresh Chatterji — Professor — NIRF DCS 2024-2025; left 2024.0
  - IIIT-D: Samrith Ram — Associate Professor — listed 2018-2022 in 5 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20220116102135/https:/
  - IIIT-D: Sandip Aine — Assistant Professor — listed 2015-2016 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20160311155551/https:/
  - IIIT-D: Shilpak Banerjee — Assistant Professor — listed 2019-2021 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20210128161655/https:/
  - IIIT-D: Shreemoy Mishra — Assistant Professor — listed 2015-2015 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20150107034827/http://
  - IIIT-D: Shweta Singh — Lecturer — listed 2020-2021 in 2 yearly snapshots as 'Lecturer'; e.g. https://web.archive.org/web/20210128161655/https://www.iiitd.
  - IIIT-D: Somitra Kr. Sanadhya — Assistant Professor — listed 2015-2017 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170129130937/http://
  - IIIT-D: Subhadip Raychaudhuri — Associate Professor — listed 2015-2019 in 5 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20190107093734/https:/
  - IIIT-D: Swapna Purandare — Associate Professor — listed 2022-2022 in 1 yearly snapshots as 'Lecturer'; e.g. https://web.archive.org/web/20220116102135/https://iiitd.ac.i
  - IIIT-D: Swati Mantri — Lecturer — listed 2020-2020 in 1 yearly snapshots as 'Lecturer'; e.g. https://web.archive.org/web/20200512203635/https://iiitd.ac.i
  - IIIT-D: Tanmoy Chakraborty — Assistant Professor — listed 2018-2022 in 5 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20220116102135/https:/
  - IIIT-D: Timothy Scott Moyers Jr — Assistant Professor — listed 2018-2019 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20190107093734/https:/
  - IIIT-D: Venkata M. Viswanath Gunturi — Assistant Professor — listed 2016-2017 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170129130937/http://
  - IIIT-D: Vinayak Naik — Associate Professor — listed 2015-2017 in 3 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20170129130937/http://
  - IIIT-H: Abdul Rehaman Moughal Shahi — Professor — listed 2015-2016 in 2 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20160123042331/http://www.iiit.a
  - IIIT-H: Abhijit Mitra — Professor Emeritus — listed 2015-2021 in 6 yearly snapshots as 'Professor Emeritus'; e.g. https://web.archive.org/web/20210115213625/https://
  - IIIT-H: Abhishek Sarkar — Research Scientist — listed 2017-2020 in 3 yearly snapshots as 'Research Scientist'; e.g. https://web.archive.org/web/20200609204529/https://
  - IIIT-H: Acharya Nand Kishore — Professor — listed 2015-2017 in 3 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20170214201405/https://www.iiit.
  - IIIT-H: Aparna Jagannathan — Visiting Assistant Professor — listed 2015-2015 in 1 yearly snapshots as 'Visiting Assistant Professor'; e.g. https://web.archive.org/web/2015020208021
  - IIIT-H: Arun Kumar Pati — Professor — listed 2023-2023 in 1 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20230202153048/https://www.iiit.
  - IIIT-H: Aruna Chaluvadi — Visiting Professor — listed 2019-2021 in 3 yearly snapshots as 'Visiting Professor'; e.g. https://web.archive.org/web/20210115213625/https://
  - IIIT-H: Bagga R. K. — Visiting Professor — listed 2015-2017 in 3 yearly snapshots as 'Visiting Professor'; e.g. https://web.archive.org/web/20170214201405/https://
  - IIIT-H: Bhaskararao Peri — Professor — listed 2015-2016 in 2 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20160123042331/http://www.iiit.a
  - IIIT-H: Chandrasekher Mukku — Research Scientist — listed 2015-2019 in 4 yearly snapshots as 'Research Scientist'; e.g. https://web.archive.org/web/20190531083330/https://
  - IIIT-H: Dipanjan Roy — Assistant Professor — listed 2015-2016 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20160123042331/http://
  - IIIT-H: Don Wallace Freeman Dcruz — Assistant Professor — listed 2020-2021 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20210115213625/https:/
  - IIIT-H: Govindarajulu R. — Professor Emeritus — listed 2015-2021 in 6 yearly snapshots as 'Professor Emeritus'; e.g. https://web.archive.org/web/20210115213625/https://
  - IIIT-H: Jolly Thomas — Visiting Assistant Professor — listed 2017-2017 in 1 yearly snapshots as 'Visiting Assistant Professor'; e.g. https://web.archive.org/web/2017021420140
  - IIIT-H: Kaul C. N. — Professor — listed 2015-2015 in 1 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20150202080215/http://www.iiit.a
  - IIIT-H: Lakshmi B.S — Visiting Professor — listed 2017-2021 in 4 yearly snapshots as 'Visiting Professor'; e.g. https://web.archive.org/web/20210115213625/https://
  - IIIT-H: Lavanya Ramapantulu — Assistant Professor — listed 2019-2020 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20200609204529/https:/
  - IIIT-H: Moumita Patra — Assistant Professor — listed 2017-2017 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170214201405/https:/
  - IIIT-H: Nagamanikandan Govindan — Assistant Professor — listed 2022-2024 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20240118040544/https:/
  - IIIT-H: Nagaraja Ravoori — Professor — listed 2022-2023 in 2 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20230202153048/https://www.iiit.
  - IIIT-H: Navjyoti Singh — Professor — listed 2015-2017 in 3 yearly snapshots as 'Professor'; e.g. https://web.archive.org/web/20170214201405/https://www.iiit.
  - IIIT-H: Neelima Satyam D. — Assistant Professor — listed 2015-2017 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170214201405/https:/
  - IIIT-H: Nishad Patnaik — Visiting Assistant Professor — listed 2019-2019 in 1 yearly snapshots as 'Visiting Assistant Professor'; e.g. https://web.archive.org/web/2019053108333
  - IIIT-H: Rahul Mishra — Assistant Professor — listed 2024-2024 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20240118040544/https:/
  - IIIT-H: Rahul Shrestha — Assistant Professor — listed 2015-2016 in 2 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20160123042331/http://
  - IIIT-H: Ram Murthy Garimella — Associate Professor — listed 2015-2017 in 3 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20170214201405/https:/
  - IIIT-H: Rambabu Kalla — Assistant Professor — listed 2015-2017 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170214201405/https:/
  - IIIT-H: Sanjay Rawat — Assistant Professor — listed 2015-2017 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170214201405/https:/
  - IIIT-H: Saswata Shannigrahi — Assistant Professor — listed 2017-2017 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170214201405/https:/
  - IIIT-H: Shubhajit Roy Chowdhury — Assistant Professor — listed 2015-2015 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20150202080215/http://
  - IIIT-H: Soma Paul — Assistant Professor — listed 2015-2020 in 5 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20200609204529/https:/
  - IIIT-H: Srivatsava Jandhyala — Assistant Professor — listed 2015-2015 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20150202080215/http://
  - IIIT-H: Subramanian Ramanathan — Associate Professor — listed 2017-2017 in 1 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20170214201405/https:/
  - IIIT-H: Sudipta Banerjee — Assistant Professor — listed 2022-2022 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20220524094902/https:/
  - IIIT-H: Supriya Mohanty — Assistant Professor — listed 2015-2017 in 3 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20170214201405/https:/
  - IIIT-H: Suril Vijaykumar Shah — Assistant Professor — listed 2015-2015 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20150202080215/http://
  - IIIT-H: Suryakanth V. Gangashetty — Assistant Professor — listed 2015-2020 in 5 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20200609204529/https:/
  - IIIT-H: Syed Azeemuddin — Associate Professor — listed 2015-2024 in 8 yearly snapshots as 'Associate Professor'; e.g. https://web.archive.org/web/20240118040544/https:/
  - IIIT-H: Ubaidulla P — Assistant Professor — listed 2015-2023 in 8 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20230202153048/https:/
  - IIIT-H: Venkata Suresh Kumar N — Research Scientist — listed 2019-2019 in 1 yearly snapshots as 'Research Scientist'; e.g. https://web.archive.org/web/20190531083330/https://
  - IIIT-H: Venkateshwarlu M — Professor Emeritus — listed 2015-2024 in 9 yearly snapshots as 'Professor Emeritus'; e.g. https://web.archive.org/web/20240118040544/https://
  - IIIT-H: Vignesh Sivaraman — Assistant Professor — listed 2022-2022 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20220524094902/https:/
  - IIIT-H: Vijaya Sankara Rao P. — Assistant Professor — listed 2015-2015 in 1 yearly snapshots as 'Assistant Professor'; e.g. https://web.archive.org/web/20150202080215/http://
  - IIIT-H: Yegnanarayana B — Emeritus Professor — listed 2015-2024 in 5 yearly snapshots as 'Emeritus Professor'; e.g. https://web.archive.org/web/20240118040544/https://
