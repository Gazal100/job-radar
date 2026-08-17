"""
Entry point: fetch -> filter/tag with Claude -> write output.
Run manually with: python scripts/run_pipeline.py
Run automatically by .github/workflows/job-scan.yml every 2 hours.
"""

import sys

import fetch_sources
import filter_with_claude
import build_output


def main():
    raw_jobs = fetch_sources.fetch_all()
    if not raw_jobs:
        print("[done] no raw jobs fetched - check API keys / network, exiting without writing output")
        sys.exit(0)

    filtered = filter_with_claude.filter_and_tag(raw_jobs)
    build_output.run(filtered)
    print("[done] pipeline complete")


if __name__ == "__main__":
    main()
