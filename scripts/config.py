"""
Central config. Edit this file to tune what the pipeline looks for.
Nothing here requires touching the pipeline logic.
"""

import os

# --- Canadian provinces/territories you want jobs from ---
# Use the two-letter codes. Leave as-is for all of Canada, or trim the list
# down to just the provinces you care about (e.g. ["ON"] for Ontario only).
TARGET_PROVINCES = ["ON", "BC", "AB", "QC", "MB", "NS", "NB", "SK", "PE", "NL", "YT", "NT", "NU"]

PROVINCE_NAMES = {
    "ON": "Ontario", "BC": "British Columbia", "AB": "Alberta", "QC": "Quebec",
    "MB": "Manitoba", "NS": "Nova Scotia", "NB": "New Brunswick", "SK": "Saskatchewan",
    "PE": "Prince Edward Island", "NL": "Newfoundland and Labrador",
    "YT": "Yukon", "NT": "Northwest Territories", "NU": "Nunavut",
}

# Also treat "Remote - Canada" / "Canada (Remote)" style postings as a match
# even if no specific province is listed.
ACCEPT_CANADA_REMOTE = True

# --- Role/keyword filter ---
# A job's title or description needs to plausibly match this to survive the
# first-pass keyword filter (Claude does the smarter semantic pass after).
ROLE_KEYWORDS = [
    "data engineer", "analytics engineer", "bi analyst", "business intelligence",
    "data analyst", "bi developer", "data platform", "etl", "elt",
    "dbt", "snowflake", "data pipeline", "power bi", "tableau",
    "azure data factory", "data scientist", "health data", "hl7", "fhir",
]

# Words that auto-disqualify a posting even if keywords match (tune freely)
EXCLUDE_KEYWORDS = ["unpaid", "internship abroad", "commission only"]

# --- Adzuna (https://developer.adzuna.com) ---
# Free account -> app_id + app_key. Country code for Canada is "ca".
ADZUNA_COUNTRY = "ca"
ADZUNA_RESULTS_PER_PAGE = 50
ADZUNA_PAGES = 3  # 3 pages x 50 = up to 150 results per run
ADZUNA_QUERY = "data engineer OR analytics engineer OR business intelligence OR data analyst"

# --- Greenhouse / Lever company boards ---
# These are PUBLIC JSON endpoints companies opt into by using these ATS
# platforms. No scraping, no auth needed. To manage a large list of companies
# (e.g. all Canadian companies), place one company slug per line in the
# data/greenhouse_companies.txt and data/lever_companies.txt files. Lines
# starting with # are treated as comments and blank lines are ignored.
#
# If the files are absent the lists fall back to the inline lists below.
# (Populating the text files is preferred for very large lists.)

GREENHOUSE_LIST_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'greenhouse_companies.txt')
LEVER_LIST_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'lever_companies.txt')


def _load_companies(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except FileNotFoundError:
        return []

# If you want to hardcode a few slugs instead of using files, put them in
# the fallback lists below.
GREENHOUSE_COMPANIES = _load_companies(GREENHOUSE_LIST_FILE) or [
    # Example: "stripe", "figma", "brex"
]

LEVER_COMPANIES = _load_companies(LEVER_LIST_FILE) or [
    # Example: "netflix", "shopify"
]

# --- Arbeitnow / RemoteOK ---
# Both are free, keyless, public JSON APIs. RemoteOK skews remote/global so
# we keep only postings that mention Canada or a Canadian province.
ENABLE_ARBEITNOW = True
ENABLE_REMOTEOK = True
ENABLE_WWR_RSS = True  # We Work Remotely RSS feed

# --- Claude filtering ---
# Haiku is fast/cheap and runs every 2 hours - good default. Bump to
# "claude-sonnet-5" if you want sharper judgment on ambiguous postings.
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_BATCH_SIZE = 25  # jobs per API call, keeps prompts manageable

# How many days back a posting can be and still be shown
MAX_POSTING_AGE_DAYS = 14
