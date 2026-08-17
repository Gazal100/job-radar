# Job Radar — Setup Guide

A GitHub Actions pipeline that pulls Canadian data/BI/analytics jobs every 2
hours from legal, ToS-compliant sources, filters them with Claude, tags them
by province, and displays results as a table in this repo.

## Why these sources and not LinkedIn/Indeed scraping

Scraping LinkedIn or Indeed HTML violates their Terms of Service, and both
have pursued legal action against scrapers in the past. Everything this
pipeline uses instead is either:
- an **official public API** (Adzuna, Arbeitnow, RemoteOK), or
- a **public JSON endpoint companies opt into** by using Greenhouse/Lever as
  their applicant tracking system (this is the standard, sanctioned way
  other job boards pull those postings), or
- a **public RSS feed** meant for redistribution (We Work Remotely)

This keeps the whole thing on solid legal ground and, practically, means it
won't silently break because your IP got blocked.

---

## Step 1 — Create the repo

1. Go to github.com → New repository.
2. Name it (e.g. `job-radar`). **Private is fine** — everything here works
   in a private repo, no GitHub Pages or paid plan required.
3. Download the files I've built and push them to the repo:

```bash
git clone https://github.com/<your-username>/job-radar.git
cd job-radar
# copy in the files from the zip I gave you
git add .
git commit -m "Initial job radar pipeline"
git push
```

## Step 2 — Get your API keys

**Anthropic API key** (for the Claude filtering step)
- Go to console.anthropic.com → Settings → API Keys → Create Key
- This is billed separately from your claude.ai subscription — check
  console.anthropic.com for current pricing. At 2-hour intervals with
  Haiku and small batches, cost is typically a few cents a day.

**Adzuna API key** (free tier, official Canadian job data)
- Go to developer.adzuna.com → Register
- You'll get an `app_id` and `app_key`. Free tier has a daily call cap —
  fine for this use case (the pipeline uses ~3 calls per run).

Arbeitnow, RemoteOK, and We Work Remotely need **no keys at all**.

## Step 3 — Add the keys as GitHub Secrets

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

Add three secrets:
| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `ADZUNA_APP_ID` | your Adzuna app id |
| `ADZUNA_APP_KEY` | your Adzuna app key |

These never appear in logs or the repo itself — Actions injects them at
runtime only.

## Step 4 — Configure what you're looking for

Open `scripts/config.py`:
- `TARGET_PROVINCES` — trim to just the provinces you want (default: all of Canada)
- `ROLE_KEYWORDS` — add/remove role keywords for the first-pass filter
- `GREENHOUSE_COMPANIES` / `LEVER_COMPANIES` — add specific companies you're
  targeting by their careers-page slug, e.g. if a company's Greenhouse board
  is at `boards.greenhouse.io/acme`, add `"acme"` to the list

## Step 5 — Turn on the schedule

The workflow in `.github/workflows/job-scan.yml` is already set to run
every 2 hours (`cron: "0 */2 * * *"`). It activates automatically once
you push to GitHub with Actions enabled (Actions is on by default for new
repos). GitHub schedules aren't millisecond-precise — during high platform
load, runs can be delayed by a few minutes, which is irrelevant for a job
feed.

To test it immediately instead of waiting: go to the **Actions** tab →
**Job Radar Scan** → **Run workflow**.

## Step 6 — View your results

Two ways, both work in a private repo with no extra setup:
1. **README.md** — auto-updates with a markdown table every run. Just open
   the repo on GitHub or the GitHub mobile app.
2. **data/jobs.json** — full structured history if you want to build
   something fancier later (a small script, a spreadsheet import, etc.)

If you later want a real hosted webpage instead of viewing it on GitHub,
GitHub Pages for a *private* repo requires GitHub Pro/Team (not the free
plan). The free-plan workaround is to make the repo public but keep the
`data/` folder as the only public part — or just stick with viewing the
README, which costs nothing and needs no extra setup.

## Costs, at a glance

- GitHub Actions: free for public repos; private repos get 2,000 free
  minutes/month, and each run here takes well under a minute
- Adzuna: free tier
- Arbeitnow / RemoteOK / WWR: free, no key
- Anthropic API: pay-as-you-go, small (check console.anthropic.com for
  current rates) — Haiku is the default model here to keep this cheap

## Extending it later

- Add a Discord/Slack webhook step to the workflow so you get pinged when a
  new high-relevance role appears, instead of checking the repo manually
- Add more Greenhouse/Lever company slugs as you identify target employers
- Swap `CLAUDE_MODEL` in `config.py` to `claude-sonnet-5` if you want
  sharper judgment on ambiguous postings (costs more per run)
