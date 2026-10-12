"""RFC 9309 robots.txt matching.

Python's urllib.robotparser applies the *first* matching rule in file order, so a file with
`Allow: /` before `Disallow: /wp-content/` would allow /wp-content/. RFC 9309 (and Google)
use the *longest* matching path; on a tie, Allow wins. This module implements the RFC rules:
  * group = the one whose user-agent token is the longest case-insensitive prefix of our
    product token; '*' only if no specific group matches; groups with the same UA merge;
  * '*' wildcard and '$' end anchor in paths; percent-encoding compared case-insensitively.
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlparse


class Robots:
    def __init__(self, text: str):
        self.groups: list[tuple[list[str], list[tuple[bool, str]], float | None]] = []
        agents: list[str] = []
        rules: list[tuple[bool, str]] = []
        delay: float | None = None
        last_was_agent = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            k, v = (x.strip() for x in line.split(":", 1))
            k = k.lower()
            if k == "user-agent":
                if not last_was_agent and (agents or rules):
                    self.groups.append((agents, rules, delay))
                    agents, rules, delay = [], [], None
                agents.append(v.lower())
                last_was_agent = True
                continue
            last_was_agent = False
            if k in ("allow", "disallow"):
                if k == "disallow" and v == "":
                    continue  # empty Disallow = allow everything
                rules.append((k == "allow", v))
            elif k == "crawl-delay":
                try:
                    delay = float(v)
                except ValueError:
                    pass
        if agents or rules:
            self.groups.append((agents, rules, delay))

    def _group(self, ua: str):
        token = ua.lower().split("/")[0].split()[0] if ua.strip() else "*"
        best, best_len, star = None, -1, None
        merged_rules: dict[str, list] = {}
        merged_delay: dict[str, float | None] = {}
        for agents, rules, delay in self.groups:
            for a in agents:
                merged_rules.setdefault(a, []).extend(rules)
                merged_delay[a] = merged_delay.get(a) or delay
        for a in merged_rules:
            if a == "*":
                star = a
            elif token.startswith(a) or a in ua.lower() and len(a) > 3:
                if len(a) > best_len:
                    best, best_len = a, len(a)
        key = best or star
        return (merged_rules.get(key, []), merged_delay.get(key)) if key else ([], None)

    @staticmethod
    def _pattern(path: str) -> re.Pattern:
        anchored = path.endswith("$")
        p = path[:-1] if anchored else path
        rx = "".join(".*" if ch == "*" else re.escape(ch) for ch in unquote(p))
        return re.compile("^" + rx + ("$" if anchored else ""))

    def can_fetch(self, ua: str, url: str) -> bool:
        rules, _ = self._group(ua)
        u = urlparse(url)
        path = unquote((u.path or "/") + (("?" + u.query) if u.query else ""))
        if path == "/robots.txt":
            return True
        best_len, allowed = -1, True
        for allow, p in rules:
            if self._pattern(p).match(path):
                ln = len(p)
                if ln > best_len or (ln == best_len and allow):
                    best_len, allowed = ln, allow
        return allowed

    def crawl_delay(self, ua: str) -> float | None:
        return self._group(ua)[1]
