"""
Phase 4: Build Citation Network.

Reads papers + authorship from the DB and builds:
  1. citation_edges table: directed edges (citing_paper -> cited_paper) where
     at least one author of the citing paper is a tracked faculty member.
     Fetched from OpenAlex /works/{id}/referenced_works for each paper.
  2. Exports three CSVs for analysis:
       papers/papers_final.csv          - all collected papers
       papers/citation_edges.csv        - citation edge list
       papers/faculty_collab_edges.csv  - co-authorship edges between faculty
"""
import sqlite3
import requests
import time
import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DB_PATH, PAPERS_DIR, OPENALEX_MAILTO, OPENALEX_SLEEP_SEC, REQUEST_TIMEOUT, RETRY_ATTEMPTS, RETRY_BACKOFF_SEC

OPENALEX_BASE = "https://api.openalex.org"

# ── helpers ────────────────────────────────────────────────────────────────────

def openalex_get(url, params=None, retries=RETRY_ATTEMPTS):
    if params is None:
        params = {}
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
                print(f"    Request failed: {e}")
            time.sleep(RETRY_BACKOFF_SEC)
    return None

# ── Step 1: init tables ────────────────────────────────────────────────────────

def init_tables(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS citation_edges (
        citing_paper_id TEXT,
        cited_paper_id  TEXT,
        PRIMARY KEY (citing_paper_id, cited_paper_id)
    );
    CREATE INDEX IF NOT EXISTS idx_ce_citing ON citation_edges(citing_paper_id);
    CREATE INDEX IF NOT EXISTS idx_ce_cited  ON citation_edges(cited_paper_id);
    """)
    conn.commit()

# ── Step 2: fetch referenced works for each paper we collected ─────────────────

def fetch_citation_edges(conn):
    paper_ids = [r[0] for r in conn.execute("SELECT paper_id FROM papers").fetchall()]
    faculty_paper_ids = set(paper_ids)

    print(f"Fetching citation edges for {len(paper_ids)} papers...")
    cursor = conn.cursor()
    edges_added = 0

    for idx, pid in enumerate(paper_ids):
        url = f"{OPENALEX_BASE}/works/{'https://openalex.org/' + pid}"
        data = openalex_get(url, {"select": "id,referenced_works"})
        if not data:
            time.sleep(OPENALEX_SLEEP_SEC)
            continue

        for ref in (data.get("referenced_works") or []):
            ref_id = ref.replace("https://openalex.org/", "")
            cursor.execute(
                "INSERT OR IGNORE INTO citation_edges (citing_paper_id, cited_paper_id) VALUES (?,?)",
                (pid, ref_id)
            )
            edges_added += 1

        time.sleep(OPENALEX_SLEEP_SEC)

        if (idx + 1) % 100 == 0:
            conn.commit()
            print(f"  [{idx+1}/{len(paper_ids)}] edges so far: {edges_added}")

    conn.commit()
    print(f"Citation edges done: {edges_added} edges for {len(paper_ids)} papers.")

# ── Step 3: export CSVs ────────────────────────────────────────────────────────

def export_csvs(conn):
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    # papers_final.csv
    papers_path = PAPERS_DIR / "papers_final.csv"
    rows = conn.execute("""
        SELECT p.paper_id, p.title, p.year, p.publication_date, p.doi,
               p.venue, p.venue_type, p.is_oa, p.cited_by_count, p.concepts_json,
               GROUP_CONCAT(pa.faculty_id, '|') AS faculty_ids,
               GROUP_CONCAT(f.institute, '|')    AS institutes,
               GROUP_CONCAT(f.name, '|')         AS faculty_names
        FROM papers p
        JOIN paper_authorship pa ON p.paper_id = pa.paper_id
        JOIN faculty f           ON pa.faculty_id = f.openalex_author_id
        GROUP BY p.paper_id
        ORDER BY p.year DESC, p.cited_by_count DESC
    """).fetchall()

    with open(papers_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["paper_id","title","year","publication_date","doi","venue","venue_type",
                    "is_oa","cited_by_count","top_concepts","faculty_ids","institutes","faculty_names"])
        w.writerows(rows)
    print(f"Exported {len(rows)} papers → {papers_path}")

    # citation_edges.csv  (only edges where CITED paper is also in our set)
    edges_path = PAPERS_DIR / "citation_edges.csv"
    our_ids_query = "SELECT paper_id FROM papers"
    edge_rows = conn.execute(f"""
        SELECT ce.citing_paper_id, ce.cited_paper_id,
               cp.year AS citing_year, rp.year AS cited_year,
               cp.venue AS citing_venue, rp.venue AS cited_venue
        FROM citation_edges ce
        JOIN papers cp ON ce.citing_paper_id = cp.paper_id
        JOIN papers rp ON ce.cited_paper_id  = rp.paper_id
    """).fetchall()

    with open(edges_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["citing_paper_id","cited_paper_id","citing_year","cited_year","citing_venue","cited_venue"])
        w.writerows(edge_rows)
    print(f"Exported {len(edge_rows)} intra-corpus citation edges → {edges_path}")

    # faculty_collab_edges.csv - co-authorship between faculty pairs
    collab_path = PAPERS_DIR / "faculty_collab_edges.csv"
    pa_rows = conn.execute("""
        SELECT pa.paper_id, pa.faculty_id, f.name, f.institute
        FROM paper_authorship pa
        JOIN faculty f ON pa.faculty_id = f.openalex_author_id
    """).fetchall()

    paper_to_authors = defaultdict(list)
    for pid, fid, fname, inst in pa_rows:
        paper_to_authors[pid].append((fid, fname, inst))

    collab_counts = defaultdict(int)
    for pid, authors in paper_to_authors.items():
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                a, b = authors[i], authors[j]
                key = tuple(sorted([a[0], b[0]]))
                collab_counts[key] += 1

    with open(collab_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["faculty_id_a","faculty_id_b","shared_papers","same_institute"])
        for (fa, fb), count in sorted(collab_counts.items(), key=lambda x: -x[1]):
            fa_inst = next((r[3] for r in pa_rows if r[1] == fa), "")
            fb_inst = next((r[3] for r in pa_rows if r[1] == fb), "")
            w.writerow([fa, fb, count, 1 if fa_inst == fb_inst else 0])
    print(f"Exported {len(collab_counts)} faculty co-authorship pairs → {collab_path}")

# ── main ───────────────────────────────────────────────────────────────────────

def run():
    conn = sqlite3.connect(DB_PATH)
    init_tables(conn)
    fetch_citation_edges(conn)
    export_csvs(conn)
    conn.close()
    print("\nCitation network build complete.")

if __name__ == "__main__":
    run()
