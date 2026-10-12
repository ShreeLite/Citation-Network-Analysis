from common.robots import Robots

IIITH = """User-agent: *
Disallow: /wp-admin/
Allow: /wp-admin/admin-ajax.php
Allow: /
Disallow: /wp-content/
Disallow: /wp-includes/
"""

CORE = """User-agent: anthropic-ai
User-agent: Claude-User
User-agent: GPTBot
Disallow: /

User-agent: *
Disallow: /core-tools/media/
"""


def test_longest_match_wins_not_first():
    r = Robots(IIITH)
    ua = "DPCN-Group9-IIIT research mapping (mailto:x@y.z)"
    assert not r.can_fetch(ua, "https://www.iiit.ac.in/wp-content/uploads/2026/04/Overall.pdf")
    assert r.can_fetch(ua, "https://www.iiit.ac.in/faculty/anoop-namboodiri/")
    assert r.can_fetch(ua, "https://www.iiit.ac.in/wp-admin/admin-ajax.php")
    assert not r.can_fetch(ua, "https://www.iiit.ac.in/wp-admin/edit.php")


def test_ai_agent_groups():
    r = Robots(CORE)
    assert not r.can_fetch("Claude-User", "https://portal.core.edu.au/conf-ranks/")
    assert not r.can_fetch("anthropic-ai", "https://portal.core.edu.au/conf-ranks/")
    assert r.can_fetch("DPCN-Group9-IIIT research mapping", "https://portal.core.edu.au/conf-ranks/")


def test_wildcards_and_delay():
    r = Robots("User-agent: *\nCrawl-delay: 10\nDisallow: /*.pdf$\nAllow: /public/*.pdf$\n")
    assert not r.can_fetch("x", "https://h/a/b.pdf")
    assert r.can_fetch("x", "https://h/public/b.pdf")
    assert r.can_fetch("x", "https://h/a/b.pdf?x=1")
    assert r.crawl_delay("x") == 10
