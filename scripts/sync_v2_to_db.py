"""
Imports disambiguation results from roster_v2_resolved.csv back into the SQLite DB.
Fills openalex_author_id, s2_author_id, google_scholar_id, dblp_pid, homepage_url.
"""
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import DB_PATH, ROSTER_DIR

V2_CSV = ROSTER_DIR / "roster_v2_resolved.csv"

def sync():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    updated = 0
    skipped = 0
    with open(V2_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fid = row.get("faculty_id", "").strip()
            if not fid:
                skipped += 1
                continue

            fields = {
                "openalex_author_id": row.get("openalex_author_id", "").strip() or None,
                "s2_author_id":       row.get("s2_author_id", "").strip() or None,
                "google_scholar_id":  row.get("google_scholar_id", "").strip() or None,
                "dblp_pid":           row.get("dblp_pid", "").strip() or None,
                "homepage_url":       row.get("homepage_url", "").strip() or None,
            }

            cursor.execute("""
                UPDATE faculty SET
                    openalex_author_id = COALESCE(?, openalex_author_id),
                    s2_author_id       = COALESCE(?, s2_author_id),
                    google_scholar_id  = COALESCE(?, google_scholar_id),
                    dblp_pid           = COALESCE(?, dblp_pid),
                    homepage_url       = COALESCE(?, homepage_url)
                WHERE faculty_id = ?
            """, (
                fields["openalex_author_id"],
                fields["s2_author_id"],
                fields["google_scholar_id"],
                fields["dblp_pid"],
                fields["homepage_url"],
                fid,
            ))
            updated += cursor.rowcount

    conn.commit()
    conn.close()

    conn2 = sqlite3.connect(DB_PATH)
    has_oa = conn2.execute("SELECT COUNT(*) FROM faculty WHERE openalex_author_id IS NOT NULL AND openalex_author_id != ''").fetchone()[0]
    has_s2 = conn2.execute("SELECT COUNT(*) FROM faculty WHERE s2_author_id IS NOT NULL AND s2_author_id != ''").fetchone()[0]
    conn2.close()

    print(f"Sync complete. Rows touched: {updated}, skipped: {skipped}")
    print(f"DB now has: {has_oa} OpenAlex IDs, {has_s2} S2 IDs")

if __name__ == "__main__":
    sync()
