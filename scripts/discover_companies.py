#!/usr/bin/env python3
"""Discover Greenhouse and Lever company slugs from public job APIs and
write them to data/greenhouse_companies.txt and data/lever_companies.txt.

This is a best-effort, non-exhaustive discovery using multiple public sources
(ArbeitNow, RemoteOK, WeWorkRemotely RSS, and public sitemaps where available).
It looks for job posting URLs or sitemap entries that indicate the posting
lives on Greenhouse or Lever and extracts the company slug. When direct
links aren't present, it heuristically probes candidate slugs based on
company names found in job postings.
"""

from __future__ import annotations
import json
import os
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
GH_FILE = os.path.join(DATA_DIR, 'greenhouse_companies.txt')
LEVER_FILE = os.path.join(DATA_DIR, 'lever_companies.txt')

HEADERS = {'User-Agent': 'job-radar-discovery/1.0 (+https://github.com/Gazal100/job-radar)'}

TIMEOUT = 12

GH_REGEX = re.compile(r"boards\.greenhouse\.io/([^/\?#]+)", re.I)

PROVINCE_KEYWORDS = [
    'canada', 'canadian', 'remote - canada', 'canada (remote)',
    'ontario', 'ont.', 'ontario,', 'quebec', 'qc', 'bc', 'british columbia',
    'alberta', 'alberta,', 'manitoba', 'saskatchewan', 'nova scotia', 'ns',
    'new brunswick', 'nb', 'newfoundland', 'pe', 'prince edward island',
]


def fetch_text(url: str):
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            return raw.decode('utf-8', errors='replace')
    except (URLError, HTTPError) as e:
        # don't spam stderr for expected 404s when probing
        return None


def fetch_json(url: str):
    txt = fetch_text(url)
    if not txt:
        return None
    try:
        return json.loads(txt)
    except Exception:
        return None


def looks_like_canadian(location: str | None) -> bool:
    if not location:
        return False
    loc = location.lower()
    return any(k in loc for k in PROVINCE_KEYWORDS)


def normalize_slug_candidates(name: str) -> list:
    if not name:
        return []
    s = name.lower()
    # remove common suffixes
    s = re.sub(r"\b(inc|inc\.|corp|co|ltd|ltd\.|llc|the)\b", '', s)
    # remove punctuation
    s = re.sub(r"[^a-z0-9\s-]", '', s)
    s = re.sub(r"\s+", ' ', s).strip()
    candidates = []
    if s:
        candidates.append(s.replace(' ', '-'))
        candidates.append(s.replace(' ', ''))
        candidates.append(s)
    # also try simple token-only candidates
    parts = s.split()
    if parts:
        candidates.extend(parts[:2])
    # unique preserving order
    seen = set()
    out = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def probe_url_exists(url: str) -> bool:
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=6) as resp:
            code = getattr(resp, 'status', None) or getattr(resp, 'getcode', lambda: None)()
            return code and int(code) < 400
    except Exception:
        return False


def probe_company_slugs_by_name(name: str, gh_set: set, lever_set: set):
    # try greenhouse candidate
    for cand in normalize_slug_candidates(name):
        gh_url = f'https://boards.greenhouse.io/{cand}'
        if probe_url_exists(gh_url):
            gh_set.add(cand)
        lever_url = f'https://jobs.lever.co/{cand}'
        if probe_url_exists(lever_url):
            lever_set.add(cand)


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def write_list(path: str, items: set):
    lst = sorted(items)
    with open(path, 'w', encoding='utf-8') as f:
        for s in lst:
            f.write(s + '\n')
    print(f'Wrote {len(lst)} entries to {path}')


def discover_from_arbeitnow(gh_set: set, lever_set: set, names: set):
    url = 'https://www.arbeitnow.com/api/job-board-api'
    data = fetch_json(url)
    if not data:
        return
    jobs = data.get('data') or []
    for job in jobs:
        location = job.get('location') or job.get('remote') or ''
        if looks_like_canadian(location):
            # collect company name for later probing
            comp = job.get('company') or job.get('company_name') or ''
            if comp:
                names.add(comp.strip())
            # try direct url extraction
            for key in ('url', 'job_ad_url'):
                extract_url = job.get(key) or ''
                if extract_url:
                    if 'boards.greenhouse.io' in extract_url:
                        m = re.search(r'boards\.greenhouse\.io/([^/\?#]+)', extract_url, re.I)
                        if m:
                            gh_set.add(m.group(1).lower())
                    if 'jobs.lever.co' in extract_url or 'lever.co' in extract_url:
                        m = re.search(r'jobs\.lever\.co/([^/\?#]+)', extract_url, re.I)
                        if m:
                            lever_set.add(m.group(1).lower())


def discover_from_remoteok(gh_set: set, lever_set: set, names: set):
    url = 'https://remoteok.com/api'
    data = fetch_json(url)
    if not data or not isinstance(data, list):
        return
    for entry in data[1:]:
        loc = entry.get('location') or ''
        if isinstance(loc, list):
            loc = ','.join(loc)
        if looks_like_canadian(loc):
            comp = entry.get('company') or entry.get('position') or ''
            if comp:
                names.add(comp.strip())
            for key in ('url', 'apply_url'):
                val = entry.get(key) or ''
                if val:
                    if 'boards.greenhouse.io' in val:
                        m = re.search(r'boards\.greenhouse\.io/([^/\?#]+)', val, re.I)
                        if m:
                            gh_set.add(m.group(1).lower())
                    if 'jobs.lever.co' in val or 'lever.co' in val:
                        m = re.search(r'jobs\.lever\.co/([^/\?#]+)', val, re.I)
                        if m:
                            lever_set.add(m.group(1).lower())


def discover_from_wwr_rss(gh_set: set, lever_set: set, names: set):
    url = 'https://weworkremotely.com/remote-jobs.rss'
    txt = fetch_text(url)
    if not txt:
        return
    for m in re.finditer(r'<item>(.*?)</item>', txt, re.S | re.I):
        item = m.group(1)
        if 'canada' in item.lower() or 'remote - canada' in item.lower():
            title_m = re.search(r'<title>(.*?)</title>', item, re.I | re.S)
            if title_m:
                # title often contains company
                names.add(re.sub(r'\s*-\s*', ' ', title_m.group(1)).strip())
            for u in re.findall(r'href=\"([^\"]+)\"', item):
                if 'boards.greenhouse.io' in u:
                    mm = re.search(r'boards\.greenhouse\.io/([^/\?#]+)', u, re.I)
                    if mm:
                        gh_set.add(mm.group(1).lower())
                if 'jobs.lever.co' in u or 'lever.co' in u:
                    mm = re.search(r'jobs\.lever\.co/([^/\?#]+)', u, re.I)
                    if mm:
                        lever_set.add(mm.group(1).lower())


def discover_from_greenhouse_sitemaps(gh_set: set):
    candidates = [
        'https://boards.greenhouse.io/sitemap.xml',
        'https://boards.greenhouse.io/sitemap/companies.xml',
        'https://boards.greenhouse.io/sitemap.xml.gz',
    ]
    for url in candidates:
        txt = fetch_text(url)
        if not txt:
            continue
        for m in re.finditer(r'boards\.greenhouse\.io/([^/\s<>"]+)', txt, re.I):
            gh_set.add(m.group(1).strip().lower())


def discover_from_lever_sitemaps(lever_set: set):
    candidates = [
        'https://jobs.lever.co/sitemap.xml',
        'https://lever.co/sitemap.xml',
    ]
    for url in candidates:
        txt = fetch_text(url)
        if not txt:
            continue
        for m in re.finditer(r'jobs\.lever\.co/([^/\s<>"]+)', txt, re.I):
            lever_set.add(m.group(1).strip().lower())


def main():
    gh_set = set()
    lever_set = set()
    names = set()

    print('Discovering from ArbeitNow...')
    discover_from_arbeitnow(gh_set, lever_set, names)

    print('Discovering from RemoteOK...')
    discover_from_remoteok(gh_set, lever_set, names)

    print('Discovering from WeWorkRemotely RSS...')
    discover_from_wwr_rss(gh_set, lever_set, names)

    print('Trying Greenhouse sitemaps...')
    discover_from_greenhouse_sitemaps(gh_set)

    print('Trying Lever sitemaps...')
    discover_from_lever_sitemaps(lever_set)

    # Probe candidate slugs derived from company names
    print(f'Probing candidate slugs for {len(names)} discovered company names...')
    for n in sorted(names):
        probe_company_slugs_by_name(n, gh_set, lever_set)

    # Deduplicate and write
    ensure_data_dir()
    write_list(GH_FILE, gh_set)
    write_list(LEVER_FILE, lever_set)

    print('\nSample Greenhouse slugs:')
    for s in sorted(list(gh_set))[:200]:
        print('  ' + s)
    print('\nSample Lever slugs:')
    for s in sorted(list(lever_set))[:200]:
        print('  ' + s)


if __name__ == '__main__':
    main()
