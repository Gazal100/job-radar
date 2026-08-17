"""
Two-stage filtering:
  1. Cheap keyword pre-filter (free, instant) to cut obvious noise
  2. Claude pass: assigns a Canadian province where identifiable, judges
     genuine role relevance, and flags duplicates across sources

Requires ANTHROPIC_API_KEY in the environment.
"""

import os
import json
import re

import anthropic
import config

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def keyword_prefilter(jobs):
    kept = []
    for j in jobs:
        blob = f"{j.get('title','')} {j.get('description','')}".lower()
        if any(bad in blob for bad in config.EXCLUDE_KEYWORDS):
            continue
        if any(k in blob for k in config.ROLE_KEYWORDS):
            kept.append(j)
    print(f"[filter] keyword pre-filter: {len(jobs)} -> {len(kept)}")
    return kept


def _chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


PROMPT_TEMPLATE = """You are screening job postings for a Canadian job search pipeline.

Target roles: data engineering, analytics engineering, BI/analytics, data science,
health data / HL7-FHIR interoperability roles. The candidate has a Python, SQL, dbt,
Snowflake, Azure Data Factory, Power BI, Tableau background.

Target Canadian provinces (2-letter codes): {provinces}
Remote postings explicitly for Canada should also be accepted.

For EACH job below, respond with a JSON array (same order, same count) where each
element is:
{{
  "keep": true/false,
  "province": "ON" | "BC" | ... | "REMOTE_CA" | "UNKNOWN" | null,
  "reason": "short reason, under 12 words"
}}

Rules:
- keep=false if the job is not in Canada / not remote-for-Canada, or is clearly
  unrelated to the target roles despite keyword overlap (e.g. "Business Intelligence"
  used in a military/defense-intel sense).
- province="UNKNOWN" if it's genuinely Canada-based but the province can't be
  determined from the text - still keep=true in that case if the role fits.
- Do not invent details not present in the text.
- Return ONLY the JSON array, no preamble, no markdown fences.

Jobs:
{jobs_json}
"""


def claude_filter_batch(batch):
    stripped = [
        {
            "title": j.get("title", "")[:200],
            "company": j.get("company", "")[:100],
            "location": j.get("location", "")[:150],
            "description": (j.get("description", "") or "")[:600],
        }
        for j in batch
    ]
    prompt = PROMPT_TEMPLATE.format(
        provinces=", ".join(config.TARGET_PROVINCES),
        jobs_json=json.dumps(stripped, ensure_ascii=False),
    )

    try:
        resp = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        verdicts = json.loads(text)
        if len(verdicts) != len(batch):
            print(f"[warn] Claude returned {len(verdicts)} verdicts for {len(batch)} jobs - skipping batch")
            return []
        return verdicts
    except Exception as e:
        print(f"[warn] Claude filter batch failed: {e}")
        return [{"keep": False, "province": None, "reason": "error"} for _ in batch]


def filter_and_tag(jobs):
    jobs = keyword_prefilter(jobs)
    if not jobs:
        return []

    results = []
    for batch in _chunks(jobs, config.CLAUDE_BATCH_SIZE):
        verdicts = claude_filter_batch(batch)
        for job, verdict in zip(batch, verdicts):
            if not verdict or not verdict.get("keep"):
                continue
            province = verdict.get("province")
            if province not in config.TARGET_PROVINCES and province != "REMOTE_CA" and province != "UNKNOWN":
                continue
            if province == "REMOTE_CA" and not config.ACCEPT_CANADA_REMOTE:
                continue
            job["province"] = province
            job["claude_reason"] = verdict.get("reason", "")
            results.append(job)

    print(f"[filter] Claude pass kept {len(results)} / {len(jobs)}")
    return dedupe(results)


def dedupe(jobs):
    seen = set()
    deduped = []
    for j in jobs:
        key = (j.get("title", "").strip().lower(), j.get("company", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    print(f"[filter] dedupe: {len(jobs)} -> {len(deduped)}")
    return deduped
