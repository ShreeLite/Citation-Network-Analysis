"""Fetch 2yr_mean_citedness (IF proxy) from OpenAlex for all journals in the dataset."""
import csv
import json
import time
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import PROCESSED, EXTERNAL, cfg

MAILTO = cfg().get("openalex", {}).get("mailto", "rickzlive3378@gmail.com")
BATCH = 50

def fetch():
    pe = pd.read_parquet(PROCESSED / "papers_enriched.parquet")
    journals = pe[pe["type"] == "journal"]
    source_ids = sorted(journals["openalex_source_id"].dropna().unique())
    print(f"Fetching IF for {len(source_ids)} unique journal sources...")

    result = {}
    for i in range(0, len(source_ids), BATCH):
        batch = source_ids[i:i + BATCH]
        filt = "openalex:" + "|".join(batch)
        url = "https://api.openalex.org/sources"
        params = {"filter": filt, "select": "id,display_name,summary_stats,type", "per-page": 200, "mailto": MAILTO}
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                for s in r.json().get("results", []):
                    sid = s["id"].replace("https://openalex.org/", "")
                    stats = s.get("summary_stats") or {}
                    citedness = stats.get("2yr_mean_citedness")
                    h = stats.get("h_index")
                    if citedness is not None:
                        result[sid] = {"display_name": s.get("display_name", ""), "two_yr_mean_citedness": citedness, "h_index": h}
            elif r.status_code == 429:
                time.sleep(5)
        except Exception as e:
            print(f"  Error at batch {i}: {e}")
        time.sleep(0.15)

        if (i // BATCH + 1) % 10 == 0:
            print(f"  Fetched {i + len(batch)}/{len(source_ids)}...")

    out_path = EXTERNAL / "openalex_source_if.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "display_name", "two_yr_mean_citedness", "h_index"])
        for sid, d in sorted(result.items()):
            w.writerow([sid, d["display_name"], d["two_yr_mean_citedness"], d["h_index"]])

    print(f"Done. {len(result)} sources with IF data → {out_path}")

if __name__ == "__main__":
    fetch()
