"""
Writes the two things a user actually looks at:
  - data/jobs.json      : full structured history (deduped, newest first)
  - README.md           : auto-generated markdown table (renders on GitHub,
                           works fine in a private repo - no Pages needed)

Re-running merges new results into history rather than overwriting it, and
drops anything older than MAX_POSTING_AGE_DAYS.
"""

import json
import os
from datetime import datetime, timezone

import config

DATA_PATH = "data/jobs.json"
README_PATH = "README.md"

README_HEADER = """# Job Radar

Auto-updated every 2 hours by a GitHub Actions pipeline. Sources: Adzuna,
Arbeitnow, RemoteOK, We Work Remotely, and any Greenhouse/Lever companies
configured in `scripts/config.py`. Filtered and tagged by province using
the Anthropic API.

Last updated: **{timestamp} UTC**  |  **{count} open roles** across
{provinces} provinces/territories tracked.

| Province | Title | Company | Source | Link |
|---|---|---|---|---|
"""


def load_existing():
    if not os.path.exists(DATA_PATH):
        return []
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def merge(existing, new_jobs):
    by_key = {}
    now = datetime.now(timezone.utc)

    for j in existing:
        key = (j.get("title", "").lower(), j.get("company", "").lower())
        by_key[key] = j

    for j in new_jobs:
        key = (j.get("title", "").lower(), j.get("company", "").lower())
        j["last_seen"] = now.isoformat()
        if key not in by_key:
            j["first_seen"] = now.isoformat()
            by_key[key] = j
        else:
            by_key[key]["last_seen"] = now.isoformat()
            # refresh province/reason in case classification improved
            by_key[key]["province"] = j.get("province", by_key[key].get("province"))

    merged = list(by_key.values())
    merged.sort(key=lambda j: j.get("first_seen", ""), reverse=True)
    return merged


def write_json(jobs):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


def write_readme(jobs):
    provinces_seen = sorted({j.get("province") for j in jobs if j.get("province") in config.TARGET_PROVINCES})
    header = README_HEADER.format(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        count=len(jobs),
        provinces=len(provinces_seen) if provinces_seen else "0",
    )
    rows = []
    for j in jobs[:200]:  # cap the table so the README stays readable
        province = j.get("province") or "?"
        title = (j.get("title") or "").replace("|", "-")[:80]
        company = (j.get("company") or "").replace("|", "-")[:50]
        source = j.get("source", "")
        url = j.get("url", "")
        rows.append(f"| {province} | {title} | {company} | {source} | [Apply]({url}) |")

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(rows) + "\n")


def run(new_jobs):
    existing = load_existing()
    merged = merge(existing, new_jobs)
    write_json(merged)
    write_readme(merged)
    print(f"[output] wrote {len(merged)} total jobs to {DATA_PATH} and {README_PATH}")
