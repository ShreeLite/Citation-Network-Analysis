from common.dedup import cluster, title_match


def rec(rid, src, title, year, doi=None, fac=("F1",), pre=False):
    return {"rid": rid, "source": src, "title": title, "year": year, "doi": doi,
            "faculty_ids": set(fac), "is_preprint": pre}


def test_doi_joins_across_sources():
    c = cluster([rec("oa1", "openalex", "Deep Nets", 2019, "10.1/x"),
                 rec("db1", "dblp", "Deep networks!", 2019, "10.1/x")])
    assert c["oa1"] == c["db1"]


def test_fuzzy_title_same_faculty_joins():
    c = cluster([rec("oa1", "openalex", "Learning to Segment Every Thing in Videos", 2020),
                 rec("db1", "dblp", "Learning to segment every thing in videos.", 2021)])
    assert c["oa1"] == c["db1"]


def test_no_join_without_shared_faculty():
    c = cluster([rec("a", "openalex", "Learning to Segment Every Thing", 2020, fac=("F1",)),
                 rec("b", "dblp", "Learning to Segment Every Thing", 2020, fac=("F2",))])
    assert c["a"] != c["b"]


def test_conference_and_journal_versions_stay_apart():
    c = cluster([rec("a", "openalex", "Robust Graph Matching", 2019, "10.1109/cvpr.1"),
                 rec("b", "openalex", "Robust Graph Matching", 2020, "10.1109/tpami.2")])
    assert c["a"] != c["b"]


def test_arxiv_collapses_into_published_with_wider_year_gap():
    c = cluster([rec("arx", "openalex", "Sparse Attention for Long Documents", 2018, "10.48550/arxiv.1801.1", pre=True),
                 rec("pub", "openalex", "Sparse Attention for Long Documents", 2020, "10.18653/v1/acl.5")])
    assert c["arx"] == c["pub"]


def test_year_gap_too_large_for_published_pair():
    c = cluster([rec("a", "openalex", "A Survey of Things", 2016), rec("b", "dblp", "A Survey of Things", 2020)])
    assert c["a"] != c["b"]


def test_short_title_not_matching_long():
    assert not title_match("graph", "graph neural networks survey benchmarks", 85)


def test_same_title_same_year_two_dois_is_one_paper():
    c = cluster([rec("a", "openalex", "Analysis of Lane Level Dynamics for Autonomous Driving", 2016, "10.5555/2936924.2937174"),
                 rec("b", "dblp", "Analysis of Lane Level Dynamics for Autonomous Driving", 2016, "10.65109/qoet5790")])
    assert c["a"] == c["b"]


def test_url_suffixed_doi_joins():
    c = cluster([rec("a", "openalex", "Analogous environments across the tree of life", 2025, "10.1093/nsr/nwaf465"),
                 rec("b", "iiith_portal", "Analogous Environments Across the Tree of Life", 2025, "10.1093/nsr/nwaf465/8305913?searchresult=1")])
    assert c["a"] == c["b"]


def test_biorxiv_counts_as_preprint_doi():
    from common.titles import is_arxiv_doi
    assert is_arxiv_doi("10.1101/387886") and not is_arxiv_doi("10.3389/fnhum.2019.00006")
