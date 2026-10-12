from common.partners import classify
from common.venues import dblp_acronym, extract_acronym, venue_key


def test_cvpr_variants_share_key():
    a = venue_key("Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)")
    b = venue_key("2021 IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)")
    c = venue_key("IEEE Conference on Computer Vision and Pattern Recognition")
    assert a == b == c == "conference computer vision pattern recognition"


def test_ordinals_and_years_removed():
    assert venue_key("Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics") == \
        venue_key("Annual Meeting of the Association for Computational Linguistics 2019")


def test_acronyms():
    assert extract_acronym("2021 IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)") == "CVPR"
    assert extract_acronym("Findings of EMNLP 2021") == "EMNLP"
    assert dblp_acronym("conf/nips") == "NeurIPS"
    assert dblp_acronym("journals/pami") == ""


def test_partner_classes():
    assert classify("Indian Institute of Technology Bombay")[0] == "IIT"
    assert classify("IIT Delhi")[0] == "IIT"
    assert classify("International Institute of Information Technology, Bangalore")[0] == "IIIT"
    assert classify("National Institute of Technology Warangal")[0] == "NIT"
    assert classify("Indian Institute of Science Education and Research Pune")[0] == "IISER"
    assert classify("Indian Institute of Science Bangalore")[0] == "IISc-TIFR"
    assert classify("CSIR - National Chemical Laboratory")[0] == "CSIR"
    assert classify("Bhabha Atomic Research Centre")[0] == "DAE"
    assert classify("University of Hyderabad")[0] == "Central University"
    assert classify("Birla Institute of Technology and Science, Pilani")[0] == "Private"
    assert classify("Osmania University", "education")[0] == "State University"
    assert classify("Tata Consultancy Services (India)", "company") == ("Other", "openalex:company")


def test_no_substring_false_positive():
    # 'nitte' (a private university) must not match inside 'committee'
    assert classify("University Grants Committee", "government")[0] == "Other"
