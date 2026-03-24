# build_sg_data.py
"""
Build site/data.json for Singapore from occupations.csv and scores.json.

Combines:
- sg_occupations.csv (for stats)
- scores.json (for AI exposure)

Output: site/data.json
"""

import csv
import json
from pathlib import Path


def main():
    # Load AI exposure scores (if available)
    scores_path = "scores.json"
    scores = {}

    if Path(scores_path).exists():
        with open(scores_path) as f:
            scores_list = json.load(f)
        scores = {s["slug"]: s for s in scores_list}

    # Load CSV stats
    with open("sg_occupations.csv") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Merge data
    data = []
    for row in rows:
        slug = row["slug"]
        score = scores.get(slug, {})

        data.append({
            "title": row["title"],
            "slug": slug,
            "category": row["category"],
            "ssoc_code": row["ssoc_code"],
            "pay": int(row["median_pay_monthly"]) if row["median_pay_monthly"] else None,
            "pay_25th": int(row["pay_25th"]) if row["pay_25th"] else None,
            "pay_75th": int(row["pay_75th"]) if row["pay_75th"] else None,
            "jobs": int(row["num_jobs_2021"]) if row["num_jobs_2021"] else None,
            "outlook": float(row["outlook_pct"]) if row["outlook_pct"] else None,
            "outlook_desc": row["outlook_desc"],
            "education": row["entry_education"],
            "exposure": score.get("exposure"),
            "exposure_rationale": score.get("rationale"),
            "url": row.get("url", ""),
        })

    # Write output
    import os
    os.makedirs("site", exist_ok=True)

    with open("site/data.json", "w") as f:
        json.dump(data, f)

    print(f"Wrote {len(data)} occupations to site/data.json")

    # Print summary
    total_jobs = sum(d["jobs"] for d in data if d["jobs"])
    print(f"Total jobs represented: {total_jobs:,}")


if __name__ == "__main__":
    main()
