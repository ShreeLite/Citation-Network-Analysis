"""Classify Indian partner institutions into the categories used for the cross-cluster panel:
IIT / NIT / IIIT / IISER / IISc-TIFR / CSIR / DAE / Central University / State University /
Private / Other. Rules are name-based; data/external/partner_type_map.csv (hand-checked)
overrides them. Every classification records which rule fired.
"""
from __future__ import annotations

import re

from unidecode import unidecode

CENTRAL_UNIVERSITIES = [
    "university of hyderabad", "jawaharlal nehru university", "university of delhi", "delhi university",
    "banaras hindu university", "aligarh muslim university", "jamia millia islamia", "pondicherry university",
    "central university", "visva-bharati", "visva bharati", "tezpur university", "assam university",
    "north-eastern hill university", "north eastern hill university", "manipur university", "mizoram university",
    "sikkim university", "nagaland university", "tripura university", "rajiv gandhi university",
    "hemvati nandan bahuguna garhwal", "guru ghasidas", "harisingh gour", "indira gandhi national tribal",
    "mahatma gandhi antarrashtriya", "english and foreign languages university", "maulana azad national urdu",
    "babasaheb bhimrao ambedkar university", "university of allahabad", "indira gandhi national open university",
    "south asian university", "nalanda university", "jamia hamdard", "national sanskrit university",
    "central agricultural university", "rani lakshmi bai central agricultural", "dr. rajendra prasad central agricultural",
    "national forensic sciences university", "gati shakti vishwavidyalaya", "sammakka sarakka central tribal",
]
PRIVATE = [
    "birla institute of technology and science", "bits pilani", "amrita vishwa vidyapeetham", "amrita university",
    "vellore institute of technology", "vit university", "manipal", "srm institute", "srm university", "ashoka university",
    "shiv nadar", "thapar institute", "kalinga institute of industrial technology", "kiit", "amity university",
    "lovely professional university", "plaksha university", "mahindra university", "o.p. jindal", "op jindal",
    "christ university", "sastra", "kalasalingam", "symbiosis", "nirma university", "pes university", "bennett university",
    "sharda university", "galgotias", "chitkara university", "krea university", "flame university", "ahmedabad university",
    "da-iict", "dhirubhai ambani", "lnm institute", "lnmiit", "jaypee", "bml munjal", "upes", "university of petroleum and energy",
    "kl university", "koneru lakshmaiah", "gitam", "sathyabama", "saveetha", "chandigarh university", "graphic era",
    "presidency university", "alliance university", "reva university", "jain university", "ramaiah", "rv college",
    "bms college", "nitte", "siksha", "anurag university", "vardhaman", "cvr college", "cbit", "chaitanya bharathi",
    "vnr vignana", "gokaraju", "mlr institute", "malla reddy", "sreenidhi", "woxsen",
    "azim premji university", "indian school of business",
    "great lakes", "xlri", "nmims", "narsee monjee", "jindal global", "sri sathya sai", "karunya", "kalasalingam",
    "sona college", "psg college", "kumaraguru", "bannari amman", "sri krishna", "rajalakshmi", "ssn college",
    "sri sivasubramaniya nadar", "hindustan institute", "vit-ap", "vit bhopal", "srm ap", "amrita school",
]
CSIR_LABS = [
    "council of scientific and industrial research", "council of scientific & industrial research", "csir",
    "national chemical laboratory", "national physical laboratory", "centre for cellular and molecular biology",
    "indian institute of chemical technology", "institute of genomics and integrative biology",
    "central electronics engineering research", "national aerospace laboratories", "central scientific instruments",
    "institute of microbial technology", "national institute of oceanography", "national geophysical research",
    "central drug research", "indian institute of chemical biology", "central leather research",
    "central glass and ceramic", "structural engineering research centre", "fourth paradigm institute",
    "national environmental engineering research", "central road research", "indian institute of integrative medicine",
    "national botanical research", "central food technological", "institute of himalayan bioresource",
    "national metallurgical laboratory", "central mechanical engineering research", "academy of scientific and innovative research",
]
DAE = [
    "bhabha atomic research", "barc", "homi bhabha national institute", "institute of physics, bhubaneswar",
    "institute of physics bhubaneswar", "saha institute of nuclear physics", "institute of mathematical sciences",
    "harish-chandra research institute", "harish chandra research institute", "raja ramanna centre",
    "indira gandhi centre for atomic research", "national institute of science education and research", "niser",
    "tata memorial", "variable energy cyclotron", "institute for plasma research", "atomic minerals directorate",
    "department of atomic energy",
]

def _words(names: list[str]) -> str:
    return "|".join(rf"\b{re.escape(n)}\b" for n in names)


RULES: list[tuple[str, str]] = [
    ("IISER", r"indian institute of science education and research|\biiser\b"),
    ("IISc-TIFR", r"indian institute of science(?! education)|\biisc\b|tata institute of fundamental research|\btifr\b|"
                  r"international centre for theoretical sciences|national centre for biological sciences"),
    ("IIIT", r"\biiit\b|iiit[\s-]|indian institute of information technology|international institute of information technology|"
             r"indraprastha institute of information technology|atal bihari vajpayee indian institute of information"),
    ("NIT", r"national institute of technology|\bnit\b|\bmnnit\b|\bvnit\b|\bsvnit\b|\bmanit\b|\bmnit\b"),
    ("IIT", r"indian institute of technology|\biit\b|\biit[\s-]"),
    ("DAE", _words(DAE)),
    ("CSIR", _words(CSIR_LABS)),
    ("Central University", _words(CENTRAL_UNIVERSITIES)),
    ("Private", _words(PRIVATE)),
]
OTHER_SUBTYPES = [
    ("IIM", r"indian institute of management|\biim\b"),
    ("AIIMS/medical", r"all india institute of medical sciences|\baiims\b|postgraduate institute of medical|\bpgimer\b|medical college|hospital"),
    ("ISRO/DRDO/defence", r"indian space research|\bisro\b|defence research|\bdrdo\b|space applications centre|vikram sarabhai"),
    ("ICMR/ICAR", r"indian council of medical research|\bicmr\b|indian council of agricultural research|\bicar\b|agricultural research institute"),
    ("ISI", r"indian statistical institute"),
    ("Government", r"ministry|government of|department of|national informatics centre|\bc-dac\b|centre for development of advanced computing"),
]


def _norm(name: str) -> str:
    return " ".join(unidecode(name or "").lower().replace("–", "-").split())


def classify(name: str, openalex_type: str | None = None, overrides: dict[str, str] | None = None) -> tuple[str, str]:
    """-> (partner_type, rule). openalex_type 'company' etc. informs the Other subtype."""
    if overrides and name in overrides:
        return overrides[name], "manual_override"
    n = _norm(name)
    for typ, pat in RULES:
        if re.search(pat, n):
            return typ, f"name:{typ}"
    for sub, pat in OTHER_SUBTYPES:
        if re.search(pat, n):
            return "Other", f"name:{sub}"
    if openalex_type == "company":
        return "Other", "openalex:company"
    if openalex_type in ("education",) and re.search(r"universit|vishwavidyalaya|vidyapeeth", n):
        return "State University", "name:university_not_central_or_private(default_state)"
    if openalex_type == "education":
        return "Other", "openalex:education_college"
    return "Other", f"openalex:{openalex_type or 'unknown'}"
