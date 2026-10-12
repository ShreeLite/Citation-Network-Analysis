# Checkpoint 2 — author matching sanity checks

## 1. Match rate

- IIIT-D current: 99/102 matched (97.1%) OK
- IIIT-D former: 37/49 matched (75.5%) BELOW 90%
  - unmatched: Acushla Saraswat (no unit, former) — no OpenAlex candidate with a similar name
  - unmatched: Anuj Kumar (ECE, current) — best candidate Anuj Kumar (A5148062652, conf 0.4, fuzzy_name_only, works 2)
  - unmatched: Ashok K. Mittal (no unit, former) — best candidate Ansh Mittal (A5041245919, conf 0.4, fuzzy_name_only, works 8)
  - unmatched: Ashwin Srinivasan (CSE, former) — best candidate Ashwin Srinivasan (A5103083219, conf 0.65, fuzzy_name+institution, works 145)
  - unmatched: K.K. Biswas (no unit, former) — best candidate Koushik Biswas (A5010852509, conf 0.65, fuzzy_name+institution, works 63)
  - unmatched: Nikhil Gupta (CSE, current) — best candidate Nikhil Gupta (A5101584977, conf 0.4, fuzzy_name_only, works 36)
  - unmatched: Prahllad Deb (MATH, current) — best candidate Prahllad Deb (A5001680567, conf 0.4, fuzzy_name_only, works 10)
  - unmatched: Pydi Ganga Mamba Bahubalindruni (ECE, former) — best candidate Pydi Ganga Bahubalindruni (A5072984355, conf 0.65, fuzzy_name+institution, works 95)
  - unmatched: Raj Ayyar (no unit, former) — best candidate Raj Ayyar (A5092263205, conf 0.4, fuzzy_name_only, works 1)
  - unmatched: Shireen Mirza (SSH, former) — best candidate Shireen Mirza (A5047286275, conf 0.4, fuzzy_name_only, works 3)
  - unmatched: Somitra Kr. Sanadhya (CSE, former) — best candidate Somitra Kumar Sanadhya (A5015932261, conf 0.65, fuzzy_name+institution, works 109)
  - unmatched: Timothy Scott Moyers Jr (HCD, former) — no OpenAlex candidate with a similar name
  - unmatched: Indrani De Parker (no unit, former) — best candidate Indrani De Parker (A5009213571, conf 0.4, fuzzy_name_only, works 3)
  - unmatched: Manohar Khushalani (no unit, former) — no OpenAlex candidate with a similar name
  - unmatched: Samaresh Chatterji (no unit, former) — no OpenAlex candidate with a similar name
- IIIT-H current: 102/109 matched (93.6%) OK
- IIIT-H former: 27/35 matched (77.1%) BELOW 90%
  - unmatched: Abdul Rehaman Moughal Shahi (no unit, former) — best candidate Abdul Rehaman Moughal Shahi (A5024107851, conf 0.4, fuzzy_name_only, works 16)
  - unmatched: Acharya Nand Kishore (no unit, former) — best candidate Nand Kishore Acharya (A5057370058, conf 0.4, fuzzy_name_only, works 14)
  - unmatched: Angarika Rakshit (HSRC, current) — best candidate Angarika Rakshit (A5118641999, conf 0.4, fuzzy_name_only, works 2)
  - unmatched: Don Wallace Freeman Dcruz (no unit, former) — best candidate Don Dcruz (A5079318207, conf 0.4, fuzzy_name_only, works 7)
  - unmatched: Isha Dubey (HSRC, current) — best candidate Isha Dubey (A5130383779, conf 0.8, dblp_doi_overlap, works 2)
  - unmatched: Kaul C. N. (no unit, former) — best candidate N-C Kaul (A5010864513, conf 0.4, fuzzy_name_only, works 1)
  - unmatched: Khaliq Parkar (HSRC, current) — best candidate Khaliq Parkar (A5040304786, conf 0.4, fuzzy_name_only, works 10)
  - unmatched: Kishore S Prahallad (LTRC, former) — best candidate Kishore Prahallad (A5113522207, conf 0.65, fuzzy_name+institution, works 58)
  - unmatched: Pawan Kumar (CSTAR, current) — best candidate Pawan Kumar (A5147428670, conf 0.88, name+last_known_institution, works 1)
  - unmatched: Rakesh Kiran Chand Thumaty (LSI, current) — best candidate Kiran Chand Thumaty (A5058930167, conf 0.65, fuzzy_name+institution, works 17)
  - unmatched: Rambabu Kalla (no unit, former) — best candidate Rambabu Kalla (A5026178435, conf 0.4, fuzzy_name_only, works 5)
  - unmatched: Rao P. R. K (no unit, former) — best candidate P Raghuveer Rao (A5123879159, conf 0.65, fuzzy_name+institution, works 4)
  - unmatched: Semparithi Aravindan (CCNSB, current) — best candidate Aravindan Semparithi (A5063171932, conf 0.4, fuzzy_name_only, works 5)
  - unmatched: Vijaya Sankara Rao P. (no unit, former) — best candidate P. Vijaya Sankara Rao (A5068595559, conf 0.65, fuzzy_name+institution, works 15)
  - unmatched: Viswanath K (SERC, current) — best candidate Kapinaiah Viswanath (A5040760446, conf 0.8, dblp_doi_overlap, works 35)

## 2. Paper counts vs DBLP (2016–2026, journal + conference)

| Faculty | Inst. | DBLP | OpenAlex (matched IDs) | Ratio | Check |
|---|---|---|---|---|---|
| Ashok Kumar Das | IIIT-H | 451 | 526 | 1.17 | ✓ |
| Tanmoy Chakraborty | IIIT-D | 268 | 290 | 1.08 | ✓ |
| Jawahar C V | IIIT-H | 268 | 286 | 1.07 | ✓ |
| Richa Singh | IIIT-D | 258 | 404 | 1.57 | MERGE? |
| Mayank Vatsa | IIIT-D | 255 | 290 | 1.14 | ✓ |
| Rajiv Ratn Shah | IIIT-D | 233 | 262 | 1.12 | ✓ |
| Kamalakar Karlapalem | IIIT-H | 47 | 47 | 1.00 | ✓ |
| Kuldeep Ramchandra Kurte | IIIT-H | 26 | 51 | 1.96 | MERGE? |
| Priyesh Shukla | IIIT-H | 13 | 18 | 1.38 | MERGE? |
| Manohar Kumar | IIIT-D | 5 | 19 | 3.80 | MERGE? |

OpenAlex also indexes non-CS venues DBLP does not cover, so ratios somewhat above 1 are expected for interdisciplinary faculty.

## 3. Most prolific and common-surname faculty (merge risk)

| Faculty | IDs | Lifetime works (sum over IDs) | Lifetime h | Top topics |
|---|---|---|---|---|
| Pushpendra Singh | 5 | 915 | 53 | Emotion and Mood Recognition; Heart Rate Variability and Autonomic Control; Non-Invasive V |
| Richa Singh | 5 | 678 | 65 | Topic Modeling; Advanced Neural Network Applications; Natural Language Processing Techniqu |
| Jawahar C V | 2 | 661 | 57 | Human Pose and Action Recognition; Autonomous Vehicle Technology and Safety; Multimodal Ma |
| Ashok Kumar Das | 9 | 636 | 92 | EEG and Brain-Computer Interfaces; Emotion and Mood Recognition; Gaze Tracking and Assisti |
| G.P.S. Raghava | 2 | 631 | 87 | Machine Learning in Bioinformatics; vaccines and immunoinformatics approaches; Computation |
| Sandeep Kumar Shukla | 4 | 578 | 35 | Information and Cyber Security; Cybercrime and Law Enforcement Studies; Cybersecurity and  |
| Vimal Bhatia | 1 | 552 | 35 | Advanced Wireless Communication Techniques; Advanced Wireless Communication Technologies;  |
| Amlan Chakrabarti | 1 | 549 | 28 | Quantum Computing Algorithms and Architecture; Embedded Systems Design Techniques; Quantum |
| Tanmoy Chakraborty | 9 | 547 | 39 | Terrorism, Counterterrorism, and Political Violence; Misinformation and Its Impacts; Menta |
| Narendra Ahuja | 1 | 545 | 75 | Advanced Vision and Imaging; Video Surveillance and Tracking Methods; Image Retrieval and  |
| Abhijit Mitra | 2 | 118 | 19 | Advanced Optical Network Technologies; Optical Network Technologies; Advanced Wireless Com |
| Amarjeet Singh | 1 | 405 | 38 | Smart Grid Energy Management; Building Energy and Comfort Optimization; Reproductive Healt |
| Anand Srivastava | 1 | 383 | 32 | Optical Wireless Communication Technologies; Protein Structure and Dynamics; Advanced Wire |
| Angshul Majumdar | 3 | 477 | 44 | Complexity and Algorithms in Graphs; Game Theory and Voting Systems; Polynomial and algebr |
| Anmol Srivastava | 1 | 61 | 6 | Augmented Reality Applications; Virtual Reality Applications and Impacts; Bacterial biofil |
| Anubha Gupta | 1 | 382 | 35 | Mathematical Analysis and Transform Methods; Sparse and Compressive Sensing Techniques; Ce |
| Anuradha Sharma | 3 | 183 | 15 | Coding theory and cryptography; Advanced Combinatorial Mathematics; Finite Group Theory Re |
| Arani Bhattacharya | 1 | 75 | 13 | IoT and Edge/Fog Computing; Network Traffic and Congestion Control; Wireless Networks and  |
| Arjun Ray | 1 | 76 | 21 | Protein Structure and Dynamics; Computational Drug Discovery Methods; Retinal Diseases and |
| Ashish Kumar Pandey | 2 | 41 | 9 | Geometric Analysis and Curvature Flows; Nonlinear Waves and Solitons; Nonlinear Dynamics a |
| Chetan Arora | 1 | 138 | 22 | Advanced Neural Network Applications; Medical Image Segmentation Techniques; Domain Adapta |
| Debidas Kundu | 2 | 66 | 14 | Advanced Antenna and Metasurface Technologies; Metamaterials and Metasurfaces Applications |
| Debika Banerjee | 1 | 28 | 3 | Analytic Number Theory Research; Advanced Mathematical Identities; Advanced Mathematical T |
| Dhruv Kumar | 18 | 509 | 43 | Topic Modeling; Intelligent Tutoring Systems and Adaptive Learning; Artificial Intelligenc |
| Diptapriyo Majumdar | 1 | 62 | 6 | Advanced Graph Theory Research; Complexity and Algorithms in Graphs; Limits and Structures |
| Gaurav Arora | 1 | 146 | 22 | Cardiac electrophysiology and arrhythmias; Cardiac Arrhythmias and Treatments; Congenital  |
| Jainendra Shukla | 1 | 73 | 11 | Emotion and Mood Recognition; Social Robot Interaction and HRI; Autism Spectrum Disorder R |
| Manohar Kumar | 2 | 22 | 5 | Ethics and Social Impacts of AI; Ethics in Business and Education; Explainable Artificial  |
| Manuj Mukherjee | 1 | 35 | 10 | Quantum Information and Cryptography; Wireless Communication Security Techniques; Cryptogr |
| Md. Shad Akhtar | 3 | 157 | 26 | Topic Modeling; Sentiment Analysis and Opinion Mining; Misinformation and Its Impacts; Mul |
| Monika Arora | 1 | 380 | 39 | Smoking Behavior and Cessation; Global Public Health Policies and Epidemiology; School Hea |
| Mrinmoy Chakrabarty | 1 | 43 | 9 | Autism Spectrum Disorder Research; Neural and Behavioral Psychology Studies; Functional Br |
| Nabanita Ray | 1 | 21 | 2 | Algebraic Geometry and Number Theory; Geometry and complex manifolds; Advanced Algebra and |
| Ojaswa Sharma | 1 | 62 | 11 | 3D Shape Modeling and Analysis; Computer Graphics and Visualization Techniques; Generative |
| Paro Mishra | 1 | 21 | 5 | South Asian Studies and Diaspora; Marriage and Family Dynamics; Bioethics and Human Rights |
| Payel C Mukherjee | 1 | 22 | 3 | Postcolonial and Cultural Literary Studies; South Asian Studies and Diaspora; Comparative  |
| Ponnurangam Kumaraguru | 1 | 433 | 44 | Misinformation and Its Impacts; Spam and Phishing Detection; Topic Modeling; Hate Speech a |
| Puneet Goyal | 1 | 80 | 14 | Advanced Neural Network Applications; Image and Video Quality Assessment; Advanced Image P |
| Rahul Purandare | 1 | 61 | 12 | Logic, programming, and type systems; Software Testing and Debugging Techniques; Formal Me |
| Rajiv Ratn Shah | 7 | 425 | 40 | Topic Modeling; Natural Language Processing Techniques; Adversarial Robustness in Machine  |
| Ram Krishna Ghosh | 1 | 126 | 22 | Crystallography and molecular interactions; Crystal structures of chemical compounds; Crys |
| Ranjitha Prasad | 1 | 57 | 10 | Privacy-Preserving Technologies in Data; Sparse and Compressive Sensing Techniques; Domain |
| Ravi Anand | 2 | 25 | 7 | Cryptographic Implementations and Security; Coding theory and cryptography; Cryptography a |
| Richa Gupta | 2 | 28 | 8 | Tactile and Sensory Interactions; Digital Accessibility for Disabilities; Synthesis and bi |
| Rinku Shah | 1 | 28 | 7 | Software-Defined Networks and 5G; Network Packet Processing and Optimization; Mobile Ad Ho |
| Sachchidanand Prasad | 1 | 10 | 3 | Geometric and Algebraic Topology; Advanced Differential Geometry Research; Geometric Analy |
| Saket Anand | 1 | 82 | 15 | Advanced Neural Network Applications; Domain Adaptation and Few-Shot Learning; Video Surve |
| Samrith Ram | 1 | 30 | 6 | Advanced Combinatorial Mathematics; Finite Group Theory Research; Matrix Theory and Algori |
| Sanat K Biswas | 1 | 52 | 10 | GNSS positioning and interference; Target Tracking and Data Fusion in Sensor Networks; Ine |
| Satish Kumar Pandey | 1 | 19 | 3 | Advanced Operator Algebra Research; Advanced Banach Space Theory; Holomorphic and Operator |
| Sayak Bhattacharya | 1 | 62 | 20 | Protein Kinase Regulation and GTPase Signaling; Gastrointestinal motility and disorders; M |
| Sayan Basu Roy | 2 | 89 | 14 | Adaptive Control of Nonlinear Systems; Control Systems and Identification; Stability and C |
| Shilpak Banerjee | 1 | 29 | 6 | Advanced Neural Network Applications; Neural Networks and Applications; Mathematical Dynam |
| Shobha Sundar Ram | 1 | 137 | 22 | Radar Systems and Signal Processing; Advanced SAR Imaging Techniques; Non-Invasive Vital S |
| Shreemoy Mishra | 1 | 9 | 2 | Banking stability, regulation, efficiency; Blockchain Technology Applications and Security |
| Smriti Singh | 1 | 84 | 8 | Postcolonial and Cultural Literary Studies; Literature: history, themes, analysis; EFL/ESL |
| Sonia Baloni Ray | 1 | 18 | 4 | Visual perception and processing mechanisms; Visual Attention and Saliency Detection; Neur |
| Sriram K | 1 | 32 | 12 | Gene Regulatory Network Analysis; Circadian rhythm and melatonin; Nonlinear Dynamics and P |
| Sujay Deb | 1 | 152 | 20 | Interconnection Networks and Systems; VLSI and FPGA Design Techniques; Parallel Computing  |
| Swapna Purandare | 1 | 11 | 7 | Hemiptera Insect Studies; Insect-Plant Interactions and Control; Animal Behavior and Repro |
| Syamantak Das | 1 | 43 | 6 | Complexity and Algorithms in Graphs; Optimization and Variational Analysis; Advanced Banac |
| Tanmoy Kundu | 1 | 8 | 4 | Robotic Path Planning Algorithms; AI-based Problem Solving and Planning; Control and Dynam |
| Tarini Shankar Ghosh | 2 | 124 | 36 | Gut microbiota and health; Oral microbiology and periodontitis research; Microbial Communi |
| Vibhor Kumar | 2 | 63 | 18 | Genomics and Chromatin Dynamics; Single-cell and spatial transcriptomics; Bioinformatics a |
| Vikram Goyal | 3 | 128 | 12 | Privacy-Preserving Technologies in Data; Topic Modeling; Data Mining Algorithms and Applic |
| Vivek Kumar | 2 | 102 | 10 | Parallel Computing and Optimization Techniques; Energy Efficient Wireless Sensor Networks; |
| Abhishek Kr Singh | 1 | 21 | 4 | Logic, programming, and type systems; Formal Methods in Verification; Software Engineering |
| Abhishek Srivastava | 4 | 63 | 9 | Radio Frequency Integrated Circuit Design; Analog and Mixed-Signal Circuit Design; Advance |
| Atul Singh Arora | 1 | 18 | 5 | Quantum Information and Cryptography; Quantum Computing Algorithms and Architecture; Crypt |
| Avinash Sharma | 2 | 177 | 16 | Computer Graphics and Visualization Techniques; 3D Shape Modeling and Analysis; Advanced V |
| Charu Sharma | 1 | 32 | 8 | 3D Shape Modeling and Analysis; Advanced Graph Neural Networks; Graph Theory and Algorithm |
| Diganta Das | 1 | 126 | 25 | Reliability and Maintenance Optimization; Electronic Packaging and Soldering Technologies; |
| Dipanjan Roy | 2 | 33 | 8 | Physical Unclonable Functions (PUFs) and Hardware Security; Advanced Steganography and Wat |
| Girish Varma | 3 | 72 | 11 | Complexity and Algorithms in Graphs; Advanced Graph Theory Research; Limits and Structures |
| Indranil Chakrabarty | 1 | 114 | 16 | Quantum Information and Cryptography; Quantum Mechanics and Applications; Quantum Computin |
| Krishna Reddy P | 2 | 138 | 23 | Data Mining Algorithms and Applications; Advanced Database Systems and Queries; Privacy-Pr |
| Marimuthu Krishnan | 1 | 48 | 14 | Protein Structure and Dynamics; Advanced Physical and Chemical Molecular Interactions; Mat |
| Navjyoti Singh | 1 | 38 | 7 | Semantic Web and Ontologies; Natural Language Processing Techniques; Sentiment Analysis an |
| Nazia akhtar | 1 | 8 | 1 | South Asian Studies and Diaspora; Literature: history, themes, analysis; Postcolonial and  |
| P Pravin Kumar Venkat Rao | 1 | 24 | 10 | Masonry and Concrete Structural Analysis; Seismic Performance and Analysis; Structural Beh |
| Ponnurangam Kumaraguru | 1 | 433 | 44 | Misinformation and Its Impacts; Spam and Phishing Detection; Topic Modeling; Hate Speech a |
| Prasad Krishnan | 2 | 67 | 9 | Cryptography and Data Security; Privacy-Preserving Technologies in Data; Cloud Data Securi |
| Priyanka Srivastava | 1 | 55 | 8 | Digital Marketing and Social Media; Virtual Reality Applications and Impacts; Neural and B |
| Priyesh Shukla | 1 | 29 | 8 | Low-power high-performance VLSI design; Advanced Memory and Neural Computing; Advanced Neu |
| Radhika Krishnan | 1 | 12 | 4 | Mining and Resource Management; Extractivism and Socioeconomic Issues; Social Sciences and |
| Rahul Mishra | 1 | 14 | 4 | Topic Modeling; Misinformation and Its Impacts; Hate Speech and Cyberbullying Detection; M |
| Rajorshi Ray | 1 | 19 | 2 | Digital Economy and Work Transformation; Digital Platforms and Economics; Legal and Labor  |
| Rama Chandra Prasad P | 1 | 57 | 16 | Remote Sensing and Land Use; Land Use and Ecosystem Services; Ecology and Vegetation Dynam |
| Samyadeb Bhattacharya | 1 | 54 | 10 | Quantum Mechanics and Applications; Quantum Information and Cryptography; Advanced Thermod |
| Sanjay Rawat | 1 | 51 | 18 | Software Testing and Debugging Techniques; Security and Verification in Computing; Network |
| Shantanav Chakraborty | 1 | 31 | 12 | Quantum Information and Cryptography; Quantum Computing Algorithms and Architecture; Quant |
| Shatrunjay Rawat | 1 | 14 | 4 | Software-Defined Networks and 5G; Network Security and Intrusion Detection; Network Traffi |
| Siddhartha Das | 3 | 43 | 17 | Quantum Information and Cryptography; Quantum Computing Algorithms and Architecture; Advan |
| Sourav Garg | 2 | 74 | 21 | Robotics and Sensor-Based Localization; Advanced Neural Network Applications; Reinforcemen |
| Spandan Roy | 1 | 269 | 32 | Advancements in Semiconductor Devices and Circuit Design; Adaptive Control of Nonlinear Sy |
| Subhadip Mitra | 2 | 95 | 20 | Particle physics theoretical and experimental studies; Quantum Chromodynamics and Particle |
| Sudipta Banerjee | 1 | 84 | 12 | Biometric Identification and Security; Digital Media Forensic Detection; Face recognition  |
| Suril Vijaykumar Shah | 1 | 90 | 17 | Robotic Mechanisms and Dynamics; Dynamics and Control of Mechanical Systems; Robotic Locom |
| Ubaidulla P | 1 | 49 | 12 | Advanced MIMO Systems Optimization; Cooperative Communication and Network Coding; Advanced |
| Uttam Singh | 3 | 33 | 15 | Quantum Mechanics and Applications; Advanced Thermodynamics and Statistical Mechanics; Qua |
| Vasudeva Varma | 2 | 371 | 32 | Topic Modeling; Natural Language Processing Techniques; Information Retrieval and Search B |
| Vinod P K | 2 | 8 | 2 | AI in cancer detection; Radiomics and Machine Learning in Medical Imaging; Computational D |
| Vishal Garg | 4 | 130 | 26 | Building Energy and Comfort Optimization; Building energy efficiency and sustainability; S |

## 4. Topic coherence

- Anindita Das (): ['Smart Agriculture and AI']
- Chetan Arora (CSE): ['AI in cancer detection']
- Dhruv Kumar (CSE): ['Fiber-reinforced polymer composites', 'Cancer, Hypoxia, and Metabolism', 'Head and Neck Cancer Studies']
- J. V. Meenakshi (SSH): ['Economics of Agriculture and Food Markets', 'Agricultural Innovations and Practices', 'Agricultural Economics and Practices']
- Rajesh Kumar (HCD): ['Lung Cancer Research Studies', 'Lung Cancer Treatments and Mutations', 'PARP inhibition in cancer therapy']
- Satish Kumar Pandey (MATH): ['Agricultural Science and Fertilization']
- Subhashree Mohapatra (MATH): ['AI in cancer detection']
- Abhijit Mitra (): ['DNA and Nucleic Acid Chemistry']
- Anirban Dasgupta (HSRC): ['Agriculture, Land Use, Rural Development']
- Anshu Sarje (CVEST): ['Analytical Chemistry and Sensors']
- Arjun Rajasekar (RCTS): ['COVID-19 Clinical Research Studies']
- Rama Chandra Prasad P (LSI): ['Remote Sensing in Agriculture']
- Syed Azeemuddin (): ['Remote Sensing in Agriculture']
- 13 faculty with topics far from their unit (computational biology/chemistry units excluded).

## 5. Shared OpenAlex IDs

- IDs assigned to more than one different person: 0 OK
- IDs shared by one person's records at both institutes (moved / adjunct): 1

## 6. Affiliation before joining

- 6 faculty with institute-affiliated papers ≥ 3 distinct years before joining (often IIIT alumni who did their PhD there; listed in qa/checkpoint2_flags.csv).

## 7. Former faculty — confirmed departures

| Former faculty | Inst. | Left (approx.) | Source | OpenAlex last known institution | Verdict |
|---|---|---|---|---|---|
| Acushla Saraswat | IIIT-D | 2022 | wayback+nirf |  | no OpenAlex match |
| Alexander Fell | IIIT-D | 2017.0 | wayback | University of Chicago | moved ✓ |
| Aman Parnami | IIIT-D | 2024 | wayback+nirf | Indraprastha Institute of Information Technology Delhi | STILL AT INSTITUTE? check |
| Amarjeet Singh | IIIT-D | 2021 | wayback+nirf | National Institute of Technology Kurukshetra; Institute of Post Gradua | moved ✓ |
| Apala Guha | IIIT-D | 2016.0 | wayback |  | no OpenAlex match |
| Ashok K. Mittal | IIIT-D | 2018.0 | wayback |  | no OpenAlex match |
| Ashwin Srinivasan | IIIT-D | 2015.0 | wayback |  | no OpenAlex match |
| Astrid Kiehn | IIIT-D | 2015.0 | wayback | Indian Institute of Technology Mandi | moved ✓ |
| Chetan Arora | IIIT-D | 2018.0 | wayback | Indian Institute of Technology Delhi | moved ✓ |
| Dhruv Kumar | IIIT-D | 2025 | wayback+nirf | Amrita Vishwa Vidyapeetham; Birla Institute of Technology and Science, | STILL AT INSTITUTE? check |
| Donghoon Chang | IIIT-D | 2024 | wayback+nirf | Indraprastha Institute of Information Technology Delhi; National Insti | STILL AT INSTITUTE? check |
| G.S. Visweswaran | IIIT-D |  | wayback+nirf | Indraprastha Institute of Information Technology Delhi | STILL AT INSTITUTE? check |
| Gourab Ghatak | IIIT-D | 2021 | wayback+nirf | Indian Institute of Technology Delhi; Delft University of Technology | moved ✓ |
| Grace Eden | IIIT-D | 2022 | wayback+nirf | University of Tartu | moved ✓ |
| Hrishikesh B. Acharya | IIIT-D | 2016.0 | wayback | Oklahoma State University | moved ✓ |
| Jatin Batra | IIIT-D | 2021.0 | wayback | Tata Institute of Fundamental Research | moved ✓ |
| Juhi Ranjan | IIIT-D | 2018.0 | wayback | University of Virginia | moved ✓ |
| K.K. Biswas | IIIT-D | 2017.0 | wayback |  | no OpenAlex match |
| Koteswar Rao Jerripothula | IIIT-D | 2025.0 | official_site | Indian Institute of Technology Kanpur | moved ✓ |
| Mayank Vatsa | IIIT-D | 2019.0 | wayback | Indian Institute of Technology Jodhpur | moved ✓ |
| Mohammad S. Hashmi | IIIT-D | 2022.0 | wayback | Nazarbayev University | moved ✓ |
| P B Sujit | IIIT-D | 2019.0 | official_site | Indian Institute of Science Education and Research, Bhopal | moved ✓ |
| Payel C Mukherjee | IIIT-D | 2025 | wayback+nirf | Indraprastha Institute of Information Technology Delhi | STILL AT INSTITUTE? check |
| Ponnurangam Kumaraguru | IIIT-D | 2021.0 | official_site | International Institute of Information Technology, Hyderabad | moved ✓ |
| Puneet Goyal | IIIT-D | 2016.0 | wayback | Indian Institute of Technology Ropar | moved ✓ |
| Pydi Ganga Mamba Bahubalindruni | IIIT-D | 2018.0 | wayback |  | no OpenAlex match |
| Rahul Purandare | IIIT-D | 2022 | wayback+nirf | University of Nebraska–Lincoln; Waseda University | moved ✓ |
| Raj Ayyar | IIIT-D | 2019.0 | wayback |  | no OpenAlex match |
| Rakesh Chaturvedi | IIIT-D |  | wayback+nirf | Universidad de Las Palmas de Gran Canaria | moved ✓ |
| Richa Singh | IIIT-D | 2019.0 | wayback | Indian Institute of Technology Jodhpur; Jawaharlal Nehru University; I | moved ✓ |
| Sachit Butail | IIIT-D | 2015.0 | wayback | Northern Illinois University | moved ✓ |
| Samrith Ram | IIIT-D | 2024 | wayback+nirf | Indraprastha Institute of Information Technology Delhi; University of  | STILL AT INSTITUTE? check |
| Sandip Aine | IIIT-D | 2016.0 | wayback | Carnegie Mellon University | moved ✓ |
| Shilpak Banerjee | IIIT-D | 2021 | wayback+nirf | Indian Institute of Technology Tirupati | moved ✓ |
| Shireen Mirza | IIIT-D | 2022 | wayback+nirf |  | no OpenAlex match |
| Shreemoy Mishra | IIIT-D | 2015.0 | wayback |  | no OpenAlex match |
| Shriram Venkatraman | IIIT-D | 2019.0 | official_site | University of Southern Denmark | moved ✓ |
| Somitra Kr. Sanadhya | IIIT-D | 2017.0 | wayback |  | no OpenAlex match |
| Subhabrata Samajder | IIIT-D | 2023.0 | official_site | TCG Crest | moved ✓ |
| Subhadip Raychaudhuri | IIIT-D | 2019.0 | wayback | Indian Institute of Advanced Research | moved ✓ |
| Swapna Purandare | IIIT-D | 2022 | wayback+nirf | Indraprastha Institute of Information Technology Delhi | STILL AT INSTITUTE? check |
| Tammam Tillo | IIIT-D |  | wayback+nirf | Indraprastha Institute of Information Technology Delhi; Taiyuan Univer | STILL AT INSTITUTE? check |
| Tanmoy Chakraborty | IIIT-D | 2022.0 | wayback | Defence Research and Development Organisation; Indian Institute of Art | STILL AT INSTITUTE? check |
| Timothy Scott Moyers Jr | IIIT-D | 2019.0 | wayback |  | no OpenAlex match |
| Venkata M. Viswanath Gunturi | IIIT-D | 2017.0 | wayback | Loughborough University | moved ✓ |
| Vinayak Naik | IIIT-D | 2017.0 | wayback | Birla Institute of Technology and Science, Pilani | moved ✓ |
| Abdul Rehaman Moughal Shahi | IIIT-H | 2016.0 | wayback |  | no OpenAlex match |
| Acharya Nand Kishore | IIIT-H | 2017.0 | wayback |  | no OpenAlex match |
| Arun Kumar Pati | IIIT-H | 2023.0 | wayback | KIIT University | moved ✓ |
| Avinash Sharma | IIIT-H | 2023.0 | official_site | Indian Institute of Technology Jodhpur; Indian Institute of Technology | moved ✓ |
| Bhaskararao Peri | IIIT-H | 2016.0 | wayback | Tokyo University of Foreign Studies | moved ✓ |
| Dipanjan Roy | IIIT-H | 2016.0 | wayback | Institute for Development and Research in Banking Technology | moved ✓ |
| Don Wallace Freeman Dcruz | IIIT-H | 2021.0 | wayback |  | no OpenAlex match |
| Kaul C. N. | IIIT-H | 2015.0 | wayback |  | no OpenAlex match |
| Kishore S Prahallad | IIIT-H | 2017.0 | official_site |  | no OpenAlex match |
| Lavanya Ramapantulu | IIIT-H | 2020.0 | wayback | International Institute of Information Technology, Hyderabad | STILL AT INSTITUTE? check |
| Moumita Patra | IIIT-H | 2017.0 | wayback | Indian Institute of Technology Guwahati | moved ✓ |
| Nagamanikandan Govindan | IIIT-H | 2024.0 | wayback | Indian Institute of Information Technology, Design and Manufacturing,  | STILL AT INSTITUTE? check |
| Nagaraja Ravoori | IIIT-H | 2023.0 | wayback | Karnataka Veterinary Animal and Fisheries Sciences University | moved ✓ |
| Navjyoti Singh | IIIT-H | 2017.0 | wayback | International Institute of Information Technology, Hyderabad | STILL AT INSTITUTE? check |
| Neelima Satyam D. | IIIT-H | 2017.0 | wayback | Indian Institute of Technology Indore | moved ✓ |
| Rahul Mishra | IIIT-H | 2024.0 | wayback | Fujitsu (Japan) | moved ✓ |
| Rahul Shrestha | IIIT-H | 2016.0 | wayback | Nepal Development Research Institute; Indian Institute of Technology M | moved ✓ |
| Ram Murthy Garimella | IIIT-H | 2017.0 | wayback | International Institute of Information Technology, Hyderabad; Mahindra | STILL AT INSTITUTE? check |
| Rambabu Kalla | IIIT-H | 2017.0 | wayback |  | no OpenAlex match |
| Rao P. R. K | IIIT-H | 2015.0 | wayback |  | no OpenAlex match |
| Sanjay Rawat | IIIT-H | 2017.0 | wayback | Technology Innovation Institute | moved ✓ |
| Saswata Shannigrahi | IIIT-H | 2017.0 | wayback | St Petersburg University | moved ✓ |
| Shubhajit Roy Chowdhury | IIIT-H | 2015.0 | wayback | Indian Institute of Technology Mandi | moved ✓ |
| Soma Paul | IIIT-H | 2020.0 | wayback | Indian Institute of Technology BHU; International Institute of Informa | STILL AT INSTITUTE? check |
| Srivatsava Jandhyala | IIIT-H | 2015.0 | wayback | International Institute of Information Technology, Hyderabad | STILL AT INSTITUTE? check |
| Subramanian Ramanathan | IIIT-H | 2017.0 | wayback | Indian Institute of Technology Ropar; University of Canberra; IMU Univ | moved ✓ |
| Sudipta Banerjee | IIIT-H | 2022.0 | wayback | University of Wyoming; Symbiosis International University | moved ✓ |
| Supriya Mohanty | IIIT-H | 2017.0 | wayback | Indian Institute of Technology BHU | moved ✓ |
| Suril Vijaykumar Shah | IIIT-H | 2015.0 | wayback | Indian Institute of Technology Jodhpur | moved ✓ |
| Suryakanth V. Gangashetty | IIIT-H | 2020.0 | wayback | International Institute of Information Technology, Hyderabad; Internat | STILL AT INSTITUTE? check |
| Syed Azeemuddin | IIIT-H | 2024.0 | wayback | Pennsylvania State University | moved ✓ |
| Ubaidulla P | IIIT-H | 2023.0 | wayback |  | no OpenAlex match |
| Vignesh Sivaraman | IIIT-H | 2022.0 | wayback | Indian Institute of Technology BHU; Banaras Hindu University | moved ✓ |
| Vijaya Sankara Rao P. | IIIT-H | 2015.0 | wayback |  | no OpenAlex match |
| Vishal Garg | IIIT-H | 2024.0 | official_site | Lawrence Berkeley National Laboratory; International Institute of Info | STILL AT INSTITUTE? check |
| Indrani De Parker | IIIT-D | 2022.0 | nirf |  | no OpenAlex match |
| Manohar Khushalani | IIIT-D | 2022.0 | nirf |  | no OpenAlex match |
| Samaresh Chatterji | IIIT-D | 2024.0 | nirf |  | no OpenAlex match |

Moved elsewhere: 44; still listing the institute: 17; no OpenAlex match: 23.

## Verdict

- Current faculty matched: IIIT-D 97%, IIIT-H 94% (target > 90%). Former faculty ~76%: mostly humanities faculty and people who left in 2015–2016 with few indexed papers; each unmatched person is listed above with the best candidate considered.
- Precision safeguards added after the first pass exposed merges: initial-only given names capped (‘A. Kumar’ ≠ ‘Anuj Kumar’), single-letter initials never count as a full match (‘K S Rajan’ ≠ ‘K. Srinathan’), DBLP records found by name alone must be topic-coherent (DBLP’s undisambiguated records pool many people), name-only matches must be topically consistent with the ORCID/DBLP-anchored profile, and ambiguous names with several topic clusters are left unmatched rather than guessed (e.g. Pawan Kumar, IIIT-H).
- DBLP counts agree within ±20% for prolific CS faculty; higher OpenAlex counts were checked by field and are non-DBLP venues (social sciences, remote sensing, medicine, mathematics).
- No OpenAlex ID is assigned to two different people; the one shared ID is Ponnurangam Kumaraguru’s, who moved from IIIT-D to IIIT-H and is an adjunct at IIIT-D.
- Every automatic decision is visible in `review/author_matches_to_review.csv` (Y/N with the reason) and `review/author_matches_dropped_by_topic_check.csv`; edit and run `make reingest` to override.
