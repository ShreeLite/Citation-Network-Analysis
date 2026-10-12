"""Project configuration, paths and secrets."""
from __future__ import annotations

import datetime as dt
import logging
import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
EXTERNAL = DATA / "external"
PROCESSED = DATA / "processed"
REVIEW = ROOT / "review"
QA = ROOT / "qa"
DELIVERABLES = ROOT / "deliverables"
FIGURES = ROOT / "report_figures"
SITE_DATA = ROOT / "site" / "src" / "data"

for _p in (RAW, CACHE, EXTERNAL, PROCESSED, REVIEW, QA, DELIVERABLES, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def cfg() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def secret(name: str, required: bool = False) -> str | None:
    val = os.environ.get(name) or None
    if required and not val:
        raise SystemExit(
            f"{name} is not set. Put it in {ROOT/'.env'} (git-ignored); see .env.example."
        )
    return val


def collection_date() -> str:
    """Date stamped on every row. Pinned in data/processed/collection_date.txt on first use
    so re-runs from cache keep the original date."""
    p = PROCESSED / "collection_date.txt"
    if p.exists():
        return p.read_text().strip()
    d = dt.date.today().isoformat()
    p.write_text(d)
    return d


def setup_logging(name: str) -> logging.Logger:
    log_dir = RAW / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format=fmt)
        fh = logging.FileHandler(log_dir / f"{name}.log")
        fh.setFormatter(logging.Formatter(fmt))
        root.addHandler(fh)
    for noisy in ("urllib3", "filelock", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger(name)
