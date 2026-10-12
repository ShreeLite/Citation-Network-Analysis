from common.names import initials_key, name_similarity, normalise
from common.titles import is_arxiv_doi, normalise_doi, normalise_title


def test_normalise_strips_honorifics_and_diacritics():
    assert normalise("Dr. Ponnurangam Kumaraguru") == "ponnurangam kumaraguru"
    assert normalise("Prof. Rāghav") == "raghav"


def test_reordered_south_indian_names():
    assert name_similarity("P. J. Narayanan", "Narayanan P J") >= 0.95
    assert initials_key("P J Narayanan") == initials_key("Narayanan, P. J.")


def test_initials_vs_full():
    assert name_similarity("C. V. Jawahar", "C V Jawahar") >= 0.95
    assert name_similarity("Vineet Gandhi", "V. Gandhi") >= 0.85
    assert name_similarity("Vikram Pudi", "Vineet Gandhi") < 0.5


def test_dropped_middle_name_and_spelling_variant():
    assert name_similarity("Ponnurangam Kumaraguru", "Ponnurangam Kumaraguru (PK)") >= 0.95
    assert name_similarity("Kamalakar Karlapalem", "Kamal Karlapalem") >= 0.6
    assert name_similarity("Srinivasa Rao Kotha", "Srinivas Kotha") >= 0.8


def test_distinct_people_with_overlapping_tokens():
    assert name_similarity("Prasad Krishnan", "Krishna Reddy P") < 0.7
    assert name_similarity("Raghu Babu Reddy Y.", "Y. Raghu Reddy") >= 0.85


def test_different_people_same_surname():
    assert name_similarity("Arun Kumar", "Ravi Kumar") < 0.7


def test_title_normalisation():
    a = normalise_title("Towards <i>Robust</i> Graph Neural Networks: A Survey")
    b = normalise_title("Robust graph neural networks - a survey.")
    assert a == b == "robust graph neural networks survey"


def test_doi_normalisation():
    assert normalise_doi("https://doi.org/10.1109/CVPR.2020.001") == "10.1109/cvpr.2020.001"
    assert is_arxiv_doi("10.48550/arXiv.2101.00001")
    assert not is_arxiv_doi("10.1145/123")
