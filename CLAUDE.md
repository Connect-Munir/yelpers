# Scraper Manual Tool

A Python + Selenium scraper that collects business details from **Yelp** and
exports them to CSV.

## What it extracts

Per business, into these CSV columns:
**Business Niche, Company Name, Location: USA, Phone Number, Yelp URL, Website URL**.

- **Business Niche** — the search term used (e.g. "restaurants", "plumbers").
- **Location: USA** — the business's full address (street, city, state, zip).
- **Website URL** — the external business site Yelp links out to (via its
  `/biz_redir?url=...` anchor).

## How it works

1. Opens a Yelp search (`/search?find_desc=<term>&find_loc=<location>`) and
   collects `/biz/<slug>` listing URLs, paginating via `&start=` in steps of 10
   until `max_results` is reached.
2. Visits each business page and reads the embedded **JSON-LD**
   (`<script type="application/ld+json">`, schema.org `LocalBusiness`) for the
   name, telephone, and address. Falls
   back to label-based XPath/regex for the phone if JSON-LD is missing, and to a
   `/biz_redir` anchor scan for the website.
3. Writes all rows to the output CSV (`utf-8-sig` so Excel opens it cleanly).

### De-duplication / append mode

With `append: true` (the default) the scraper **merges** into the existing
output CSV instead of overwriting it, keyed on the `Yelp URL` column:

- URLs already present in the CSV are **skipped before scraping** (fewer
  requests = less chance of being blocked).
- Re-scraped businesses **refresh** their existing row rather than adding a
  duplicate; the newest scrape wins.
- This lets you run several searches (different terms/cities) into one growing,
  duplicate-free file.

Set `append: false` in `config.json` (or pass `--no-append`) to overwrite the
file each run instead.

## Project layout

- `scraper.py` — the scraper (search -> per-business extraction -> CSV).
- `config.json` — default search term, location, limits, delays, output path.
- `output.csv` — generated results (created on run).

```

Requires Python 3.10+ and Google Chrome installed. Selenium 4.6+ downloads the
matching chromedriver automatically (Selenium Manager) — no manual driver setup.

## Run

```powershell
# Uses config.json
python scraper.py

# Or override on the command line
python scraper.py --term "plumbers" --location "Austin, TX" --max 30
python scraper.py --headless --out results.csv
python scraper.py --no-append            # overwrite output.csv instead of merging
```

CLI flags override `config.json`. Available: `--term`, `--location`, `--max`,
`--out`, `--headless`, `--no-append`.

## Important Yelp-specific caveats

- **Anti-bot protection (DataDome).** Yelp serves a "verify you are a human"
  CAPTCHA (a `geo.captcha-delivery.com` iframe) on the search/home pages, and
  sometimes on business pages. The scraper uses
  [`undetected-chromedriver`](https://pypi.org/project/undetected-chromedriver/),
  a realistic profile, and randomized delays (`delay_min`/`delay_max`). On
  startup it opens the homepage as a warm-up: **if the CAPTCHA appears, solve it
  once in the visible Chrome window and press ENTER.** DataDome then sets a
  clearance cookie that is reused (the scraper keeps a persistent Chrome profile
  in `.chrome-profile/`), so the search and business pages load cleanly for the
  rest of the run. This only works non-headless (`"headless": false`, the
  default) — headless has no one to solve the challenge.
- **Block detection.** Blocking is detected by the presence of the CAPTCHA
  iframe (and an empty interstitial page), **not** by scanning page text — Yelp
  embeds the DataDome script in every normal page, so a text scan would
  false-flag good pages (and never recognise success after you solve it).
- **Email is not collected.** Yelp does not publish business email addresses;
  the `Website URL` column is the practical contact link.
- **Terms of Service.** Yelp's ToS prohibit automated scraping. Keep volumes
  low and use only for authorized/personal purposes.

## Tuning

Edit `config.json`:

- `headless` — `true` runs without a visible window (more likely to be flagged).
- `delay_min` / `delay_max` — seconds of random pause between requests; raise
  these if you get blocked.
- `page_load_timeout` — per-page load timeout in seconds.
