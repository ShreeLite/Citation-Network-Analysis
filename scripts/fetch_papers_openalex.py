"""
Phase 3: Paper collection via OpenAlex.

For every faculty with an openalex_author_id, fetches all works published
between their start_date and end_date (capped to 2016-2026 per project scope).
Stores results in the 'papers' and 'paper_authorship' tables.
"""
import sqlite3
import requests
import time
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DB_PATH, OPENALEX_MAILTO, OPENALEX_SLEEP_SEC, REQUEST_TIMEOUT, RETRY_ATTEMPTS, RETRY_BACKOFF_SEC

PROJECT_START = 2016
PROJECT_END   = 2026

OPENALEX_BASE = "https://api.openalex.org"

def init_paper_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS papers (
        paper_id        TEXT PRIMARY KEY,
        title           TEXT,
        year            INTEGER,
        publication_date TEXT,
        doi             TEXT,
        venue           TEXT,
        venue_type      TEXT,
        is_oa           INTEGER,
        cited_by_count  INTEGER,
        concepts_json   TEXT,
        raw_json        TEXT
    );

    CREATE TABLE IF NOT EXISTS paper_authorship (
        paper_id        TEXT,
        faculty_id      TEXT,
        author_position TEXT,
        is_corresponding INTEGER DEFAULT 0,
        PRIMARY KEY (paper_id, faculty_id)
    );

    CREATE INDEX IF NOT EXISTS idx_pa_faculty ON paper_authorship(faculty_id);
    CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
    """)
    conn.commit()

def openalex_get(url, params, retries=RETRY_ATTEMPTS):
    params["mailto"] = OPENALEX_MAILTO
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
        except Exception as e:
            if attempt == retries - 1:
                print(f"    Request failed after {retries} attempts: {e}")
            time.sleep(RETRY_BACKOFF_SEC)
    return None

def faculty_active_window(start_date, end_date):
    """Return (from_year, to_year) clamped to project scope."""
    try:
        from_year = int(str(start_date)[:4]) if start_date else PROJECT_START
    except Exception:
        from_year = PROJECT_START
    from_year = max(from_year, PROJECT_START)

    if end_date and str(end_date).lower() not in ("present", "current", ""):
        try:
            to_year = int(str(end_date)[:4])
        except Exception:
            to_year = PROJECT_END
    else:
        to_year = PROJECT_END
    to_year = min(to_year, PROJECT_END)

    return from_year, to_year

def fetch_works_for_author(openalex_id, from_year, to_year):
    """Fetch all works for an author in [from_year, to_year] via cursor pagination."""
    works = []
    cursor = "*"
    url = f"{OPENALEX_BASE}/works"

    while True:
        params = {
            "filter": f"author.id:{openalex_id},publication_year:{from_year}-{to_year}",
            "per-page": 200,
            "cursor": cursor,
            "select": "id,title,publication_year,publication_date,doi,primary_location,type,open_access,cited_by_count,concepts,authorships",
        }
        data = openalex_get(url, params)
        if not data:
            break

        batch = data.get("results", [])
        works.extend(batch)
        time.sleep(OPENALEX_SLEEP_SEC)

        meta = data.get("meta", {})
        cursor = meta.get("next_cursor")
        if not cursor or not batch:
            break

    return works

def upsert_paper(cursor, work, faculty_id):
    paper_id = work.get("id", "").replace("https://openalex.org/", "")
    if not paper_id:
        return

    loc = work.get("primary_location") or {}
    source = loc.get("source") or {}
    venue = source.get("display_name", "")
    venue_type = work.get("type", "")
    oa = 1 if (work.get("open_access") or {}).get("is_oa") else 0
    concepts = json.dumps([c.get("display_name") for c in (work.get("concepts") or [])[:5]])
    raw = json.dumps({k: work[k] for k in ("id","title","publication_year","doi","authorships") if k in work})

    cursor.execute("""
        INSERT OR IGNORE INTO papers
            (paper_id, title, year, publication_date, doi, venue, venue_type, is_oa, cited_by_count, concepts_json, raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        paper_id,
        work.get("title", ""),
        work.get("publication_year"),
        work.get("publication_date", ""),
        work.get("doi", ""),
        venue,
        venue_type,
        oa,
        work.get("cited_by_count", 0),
        concepts,
        raw,
    ))

    # Find this author's position in the authorship list
    position = "unknown"
    is_corr = 0
    for auth in (work.get("authorships") or []):
        author_obj = auth.get("author") or {}
        aid = author_obj.get("id", "").replace("https://openalex.org/", "")
        if aid and aid in faculty_id:  # faculty_id is the openalex id
            position = auth.get("author_position", "unknown")
            is_corr = 1 if auth.get("is_corresponding") else 0
            break

    cursor.execute("""
        INSERT OR IGNORE INTO paper_authorship (paper_id, faculty_id, author_position, is_corresponding)
        VALUES (?,?,?,?)
    """, (paper_id, faculty_id, position, is_corr))

def run():
    conn = sqlite3.connect(DB_PATH)
    init_paper_tables(conn)

    rows = conn.execute("""
        SELECT faculty_id, name, institute, openalex_author_id, start_date, end_date
        FROM faculty
        WHERE openalex_author_id IS NOT NULL AND openalex_author_id != ''
        ORDER BY institute, name
    """).fetchall()

    print(f"Fetching papers for {len(rows)} faculty with OpenAlex IDs...")
    total_papers = 0
    cursor = conn.cursor()

    for idx, (fid, name, inst, oa_id, start_date, end_date) in enumerate(rows):
        from_year, to_year = faculty_active_window(start_date, end_date)
        if from_year > to_year:
            continue

        works = fetch_works_for_author(oa_id, from_year, to_year)
        for work in works:
            upsert_paper(cursor, work, oa_id)
        total_papers += len(works)

        if (idx + 1) % 20 == 0:
            conn.commit()
            print(f"  [{idx+1}/{len(rows)}] {name} ({inst}): {len(works)} papers | total so far: {total_papers}")

    conn.commit()

    final_papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    final_links  = conn.execute("SELECT COUNT(*) FROM paper_authorship").fetchone()[0]
    conn.close()

    print(f"\nDone. {final_papers} unique papers, {final_links} authorship links collected.")

if __name__ == "__main__":
    run()
