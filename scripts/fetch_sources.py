"""
Pulls raw postings from legal, ToS-compliant sources only:
  - Adzuna API (official, requires free app_id/app_key)
  - Arbeitnow API (free, public, keyless)
  - RemoteOK API (free, public, keyless)
  - We Work Remotely RSS (public RSS feed, meant for redistribution)
  - Greenhouse / Lever public job-board JSON endpoints (companies opt into
    these being public by using these ATS platforms)

Nothing here scrapes LinkedIn, Indeed, or Glassdoor HTML - those are
explicitly excluded because scraping them violates their Terms of Service.
"""

import os
import time
import requests
import feedparser

import config

HEADERS = {"User-Agent": "job-radar/1.0 (personal job search tool)"}


def _get(url, params=None, timeout=20):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[warn] request failed for {url}: {e}")
        return None


def fetch_adzuna():
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("[skip] Adzuna: ADZUNA_APP_ID / ADZUNA_APP_KEY not set")
        return []

    jobs = []
    for page in range(1, config.ADZUNA_PAGES + 1):
        url = f"https://api.adzuna.com/v1/api/jobs/{config.ADZUNA_COUNTRY}/search/{page}"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": config.ADZUNA_RESULTS_PER_PAGE,
            "what": config.ADZUNA_QUERY,
            "content-type": "application/json",
        }
        data = _get(url, params=params)
        if not data or "results" not in data:
            break
        for j in data["results"]:
            jobs.append({
                "title": j.get("title", ""),
                "company": (j.get("company") or {}).get("display_name", "Unknown"),
                "location": (j.get("location") or {}).get("display_name", ""),
                "url": j.get("redirect_url", ""),
                "description": j.get("description", ""),
                "posted_at": j.get("created", ""),
                "source": "Adzuna",
            })
        time.sleep(0.5)
    print(f"[ok] Adzuna: {len(jobs)} postings")
    return jobs


def fetch_arbeitnow():
    if not config.ENABLE_ARBEITNOW:
        return []
    data = _get("https://www.arbeitnow.com/api/job-board-api")
    if not data:
        return []
    jobs = []
    for j in data.get("data", []):
        jobs.append({
            "title": j.get("title", ""),
            "company": j.get("company_name", "Unknown"),
            "location": j.get("location", ""),
            "url": j.get("url", ""),
            "description": j.get("description", ""),
            "posted_at": str(j.get("created_at", "")),
            "source": "Arbeitnow",
        })
    print(f"[ok] Arbeitnow: {len(jobs)} postings")
    return jobs


def fetch_remoteok():
    if not config.ENABLE_REMOTEOK:
        return []
    data = _get("https://remoteok.com/api")
    if not data:
        return []
    jobs = []
    for j in data:
        if not isinstance(j, dict) or "position" not in j:
            continue  # first element is a metadata blob, skip it
        location = j.get("location", "") or ""
        # RemoteOK is global-remote by default; only keep Canada-relevant ones
        if "canada" not in location.lower() and "ca" != location.lower():
            continue
        jobs.append({
            "title": j.get("position", ""),
            "company": j.get("company", "Unknown"),
            "location": location,
            "url": j.get("url", ""),
            "description": j.get("description", ""),
            "posted_at": str(j.get("date", "")),
            "source": "RemoteOK",
        })
    print(f"[ok] RemoteOK: {len(jobs)} Canada-relevant postings")
    return jobs


def fetch_wwr_rss():
    if not config.ENABLE_WWR_RSS:
        return []
    feed_url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    parsed = feedparser.parse(feed_url)
    jobs = []
    for entry in parsed.entries:
        jobs.append({
            "title": entry.get("title", ""),
            "company": "",  # WWR bundles company into the title
            "location": "Remote",
            "url": entry.get("link", ""),
            "description": entry.get("summary", ""),
            "posted_at": entry.get("published", ""),
            "source": "We Work Remotely",
        })
    print(f"[ok] We Work Remotely RSS: {len(jobs)} postings")
    return jobs


def fetch_greenhouse():
    jobs = []
    for slug in config.GREENHOUSE_COMPANIES:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        data = _get(url)
        if not data:
            continue
        for j in data.get("jobs", []):
            jobs.append({
                "title": j.get("title", ""),
                "company": slug,
                "location": (j.get("location") or {}).get("name", ""),
                "url": j.get("absolute_url", ""),
                "description": "",
                "posted_at": j.get("updated_at", ""),
                "source": f"Greenhouse:{slug}",
            })
    if config.GREENHOUSE_COMPANIES:
        print(f"[ok] Greenhouse: {len(jobs)} postings across {len(config.GREENHOUSE_COMPANIES)} companies")
    return jobs


def fetch_lever():
    jobs = []
    for slug in config.LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        data = _get(url)
        if not data:
            continue
        for j in data:
            categories = j.get("categories", {}) or {}
            jobs.append({
                "title": j.get("text", ""),
                "company": slug,
                "location": categories.get("location", ""),
                "url": j.get("hostedUrl", ""),
                "description": "",
                "posted_at": str(j.get("createdAt", "")),
                "source": f"Lever:{slug}",
            })
    if config.LEVER_COMPANIES:
        print(f"[ok] Lever: {len(jobs)} postings across {len(config.LEVER_COMPANIES)} companies")
    return jobs


def fetch_all():
    jobs = []
    jobs += fetch_adzuna()
    jobs += fetch_arbeitnow()
    jobs += fetch_remoteok()
    jobs += fetch_wwr_rss()
    jobs += fetch_greenhouse()
    jobs += fetch_lever()
    print(f"[total] {len(jobs)} raw postings pulled from all sources")
    return jobs
