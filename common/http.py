"""Cached, rate-limited, retrying HTTP layer.

Every response body is written to data/cache/<source>/<xx>/<sha1>.<ext> together with a
.meta.json sidecar (url, status, fetched_at). A cache hit never touches the network, so any
step can be re-run or resumed after a crash without re-downloading. Secrets (api_key) are
excluded from the cache key and from logs.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from . import tls
from .robots import Robots
from .config import CACHE, RAW, cfg

log = logging.getLogger("http")

SECRET_PARAMS = {"api_key", "mailto"}
PERMANENT_STATUSES = {400, 401, 403, 404, 410}
NEG_TTL = 7 * 24 * 3600  # seconds a network failure is remembered (source 'web' only)


class BudgetExhausted(RuntimeError):
    """OpenAlex daily credit budget used up. Re-run after reset; everything so far is cached."""


class TransientHTTPError(RuntimeError):
    pass


class PermanentHTTPError(RuntimeError):
    def __init__(self, url: str, status: int, body: str = ""):
        super().__init__(f"HTTP {status} for {url}")
        self.status = status
        self.body = body


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, requests.exceptions.SSLError):
        return False  # certificate problems do not fix themselves
    return isinstance(exc, (TransientHTTPError, requests.ConnectionError, requests.Timeout))


def _looks_like_challenge(body: bytes, ext: str) -> bool:
    head = body[:600].lstrip().lower()
    if ext == "json":
        try:
            json.loads(body)
            return False
        except ValueError:
            return True
    return head.startswith(b"<!doctype html") or b"not a bot" in head


class _RateLimiter:
    def __init__(self, interval: float):
        self.interval = interval
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                time.sleep(self._next - now)
            self._next = max(now, self._next) + self.interval


_log_lock = threading.Lock()


def _log_request(entry: dict) -> None:
    with _log_lock, open(RAW / "request_log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def cache_key(url: str, params: dict | None, data: dict | None = None, json_body=None) -> str:
    clean = {k: v for k, v in (params or {}).items() if k not in SECRET_PARAMS}
    full = url + ("?" + urlencode(sorted(clean.items()), doseq=True) if clean else "")
    if data is not None:  # POST: body is part of the identity of the request
        full = "POST " + full + " " + urlencode(sorted(data.items()), doseq=True)
    if json_body is not None:
        full = "POSTJSON " + full + " " + json.dumps(json_body, sort_keys=True)
    return hashlib.sha1(full.encode()).hexdigest()


class Fetcher:
    """One instance per source (openalex, dblp, crossref, s2, ror, wayback, web, ...)."""

    def __init__(
        self,
        source: str,
        interval: float | None = None,
        headers: dict | None = None,
        default_params: dict | None = None,
        obey_robots: bool = False,
        timeout: float = 60,
        max_attempts: int = 7,
        max_wait: float = 120,
        negative_cache: bool = False,
    ):
        self.source = source
        self.dir = CACHE / source
        self.dir.mkdir(parents=True, exist_ok=True)
        rl = cfg()["rate_limits"]
        self.limiter = _RateLimiter(interval if interval is not None else rl.get(source, 1.0))
        self.session = requests.Session()
        self.session.headers["User-Agent"] = cfg()["user_agent"]
        if headers:
            self.session.headers.update(headers)
        self.default_params = default_params or {}
        self.obey_robots = obey_robots
        self.timeout = timeout
        self.max_attempts, self.max_wait = max_attempts, max_wait
        self.negative_cache = negative_cache
        self._robots: dict[str, Robots | None] = {}
        self._host_limiters: dict[str, _RateLimiter] = {}
        self._tls_repaired: set[str] = set()
        self.session.verify = tls.bundle_path()
        self.stats = {"hit": 0, "miss": 0}

    # ---------- cache ----------
    def _paths(self, key: str, ext: str) -> tuple[Path, Path]:
        d = self.dir / key[:2]
        return d / f"{key}.{ext}", d / f"{key}.meta.json"

    def cached(self, url: str, params: dict | None = None, ext: str = "json") -> bool:
        body, meta = self._paths(cache_key(url, params), ext)
        return meta.exists()

    def _session_get(self, url: str, data: dict | None = None, json_body=None, **kw) -> requests.Response:
        """GET (or POST when `data` is given) that repairs incomplete TLS chains once per
        host (never verify=False)."""
        host = urlparse(url).netloc.split(":")[0]
        if json_body is not None:
            call = lambda: self.session.post(url, json=json_body, timeout=(10, self.timeout), **kw)  # noqa: E731
        elif data is not None:
            call = lambda: self.session.post(url, data=data, timeout=(10, self.timeout), **kw)  # noqa: E731
        else:
            call = lambda: self.session.get(url, timeout=(10, self.timeout), **kw)  # noqa: E731
        try:
            return call()
        except requests.exceptions.SSLError:
            if host in self._tls_repaired:
                raise
            log.warning("TLS chain incomplete for %s; fetching intermediates via AIA", host)
            self.session.verify = tls.repair_chain(host)
            self._tls_repaired.add(host)
            return call()

    # ---------- robots ----------
    def allowed(self, url: str) -> bool:
        if not self.obey_robots:
            return True
        host = urlparse(url)
        base = f"{host.scheme}://{host.netloc}"
        if base not in self._robots:
            try:
                r = self._session_get(base + "/robots.txt")
                rp = Robots(r.text if r.status_code == 200 else "")
            except requests.RequestException:
                rp = None  # unreachable robots.txt: treat as allow, but log
                log.warning("robots.txt unreachable for %s", base)
            self._robots[base] = rp
            delay = rp.crawl_delay(self.session.headers["User-Agent"]) if rp else None
            if delay:
                log.info("honouring Crawl-delay %ss for %s", delay, base)
                self._host_limiters[host.netloc] = _RateLimiter(max(float(delay), self.limiter.interval))
        rp = self._robots[base]
        if rp is None:
            return True
        # Requests are made by an AI agent on the user's behalf: honour rules aimed at our own
        # UA *and* at Claude-User / anthropic-ai.
        return all(rp.can_fetch(ua, url) for ua in (self.session.headers["User-Agent"], "Claude-User", "anthropic-ai"))

    # ---------- network ----------
    def _fetch(self, *a, **kw) -> requests.Response:
        """Retry transient failures with exponential backoff. APIs get 7 attempts (up to 2 min
        apart); personal homepages (source 'web') get 3 short attempts so a dead site costs
        seconds, not minutes."""
        for attempt in Retrying(retry=retry_if_exception(_is_transient), reraise=True,
                                wait=wait_exponential_jitter(initial=2, max=self.max_wait),
                                stop=stop_after_attempt(self.max_attempts)):
            with attempt:
                return self._fetch_once(*a, **kw)

    def _fetch_once(self, url: str, params: dict, headers: dict | None, data: dict | None = None, json_body=None) -> requests.Response:
        host = urlparse(url).netloc
        self._host_limiters.get(host, self.limiter).wait()
        r = self._session_get(url, data=data, json_body=json_body, params=params, headers=headers)
        if r.status_code == 429:
            body = r.text[:500]
            if self.source == "openalex" and ("budget" in body.lower() or "Insufficient" in body):
                reset = r.headers.get("x-ratelimit-reset") or r.headers.get("retry-after")
                raise BudgetExhausted(
                    f"OpenAlex daily budget exhausted; resets in {reset}s. Re-run the same step "
                    "after reset — all completed requests are cached."
                )
            ra = r.headers.get("retry-after")
            if ra and ra.isdigit() and int(ra) <= 120:
                time.sleep(int(ra))
            raise TransientHTTPError(f"429 for {url}")
        if r.status_code >= 500:
            raise TransientHTTPError(f"{r.status_code} for {url}")
        return r

    def get(
        self,
        url: str,
        params: dict | None = None,
        ext: str = "json",
        headers: dict | None = None,
        use_cache: bool = True,
        data: dict | None = None,
        json_body=None,
    ):
        """Return parsed JSON (ext=json), str (html/xml/txt/csv) or bytes (bin).
        Pass `data` for a form POST (read-only search endpoints only).
        Raises PermanentHTTPError for 4xx (also cached, so it is not re-requested)."""
        params = dict(params or {})
        key = cache_key(url, params, data, json_body)
        body_p, meta_p = self._paths(key, ext)
        if use_cache and meta_p.exists():
            meta = json.loads(meta_p.read_text())
            if meta["status"] == -1 and time.time() - meta.get("epoch", 0) > NEG_TTL:
                meta_p.unlink()  # negative entry expired: try the network again
            else:
                self.stats["hit"] += 1
                if meta["status"] != 200:
                    raise PermanentHTTPError(url, meta["status"], meta.get("body", ""))
                return self._decode(body_p, ext)

        if not self.allowed(url):
            raise PermanentHTTPError(url, 999, "disallowed by robots.txt")

        full_params = {**self.default_params, **params}
        t0 = time.time()
        try:
            r = self._fetch(url, full_params, headers, data, json_body)
        except (requests.ConnectionError, requests.Timeout) as e:
            if self.negative_cache:  # dead host / DNS failure: remember for NEG_TTL so re-runs stay fast
                body_p.parent.mkdir(parents=True, exist_ok=True)
                meta_p.write_text(json.dumps({"url": url, "status": -1, "epoch": time.time(), "body": str(e)[:200]}))
            raise
        self.stats["miss"] += 1
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": self.source,
            "url": url,
            "params": {k: v for k, v in params.items() if k not in SECRET_PARAMS},
            "method": "POST" if (data is not None or json_body is not None) else "GET",
            "status": r.status_code,
            "secs": round(time.time() - t0, 2),
            "credits_remaining": r.headers.get("x-ratelimit-remaining"),
        }
        _log_request(entry)

        body_p.parent.mkdir(parents=True, exist_ok=True)
        meta = {"url": url, "params": entry["params"], "status": r.status_code,
                "fetched_at": entry["ts"], "final_url": r.url.split("api_key=")[0]}
        if r.status_code != 200:
            if r.status_code in PERMANENT_STATUSES:
                meta["body"] = r.text[:300]
                meta_p.write_text(json.dumps(meta))
            raise PermanentHTTPError(url, r.status_code, r.text[:300])
        if ext in ("json", "xml") and _looks_like_challenge(r.content, ext):
            # bot-check / challenge pages (e.g. Anubis) arrive as HTTP 200: never cache them,
            # and do not try to get around them.
            raise PermanentHTTPError(url, 403, "bot-check challenge page instead of data")
        tmp = body_p.with_suffix(body_p.suffix + ".tmp")
        tmp.write_bytes(r.content)
        tmp.replace(body_p)  # atomic: a crash never leaves a half-written cache entry
        meta_p.write_text(json.dumps(meta))
        return self._decode(body_p, ext)

    @staticmethod
    def _decode(p: Path, ext: str):
        if ext == "json":
            return json.loads(p.read_bytes())
        if ext == "bin":
            return p.read_bytes()
        return p.read_bytes().decode("utf-8", errors="replace")
