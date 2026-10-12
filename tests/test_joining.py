from common.joining import extract_joining_year


def test_explicit_joined():
    y, c, _ = extract_joining_year("She joined IIIT-Delhi in July 2017 as an Assistant Professor.", "IIIT-D")
    assert (y, c) == (2017, 0.9)


def test_since_with_institute():
    y, c, _ = extract_joining_year("He has been a faculty member at IIIT Hyderabad since 2012.", "IIIT-H")
    assert y == 2012 and c >= 0.85


def test_cv_range():
    text = "Experience\n2016 – Present  Assistant Professor, Indraprastha Institute of Information Technology Delhi\n2014 – 2016 Postdoc, MIT"
    y, c, _ = extract_joining_year(text, "IIIT-D")
    assert y == 2016 and c == 0.8


def test_other_institute_not_matched():
    y, _, _ = extract_joining_year("He joined IIT Bombay in 2015.", "IIIT-H")
    assert y is None


def test_conflict_lowers_confidence():
    text = "Joined IIIT Hyderabad in 2010. ... at IIIT Hyderabad since 2014."
    y, c, ev = extract_joining_year(text, "IIIT-H")
    assert y == 2010 and c <= 0.6 and ev.startswith("CONFLICT")
