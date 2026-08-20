# Refresh Guide — keeping the Canada overheating analysis up to date

How and when to update the data behind the AM overheating index. See `ROADMAP.md` for
the methodology and `fetch_data.py` for the fetch/cache code.

## TL;DR

```bash
cd /home/ethan13/Disaster-Prediction
.venv/bin/python fetch_data.py --refresh     # re-pull every series into data/raw/
```

Then (once the analysis pipeline from Phases 2–4 is built) recompute and rebuild the page.
For now, `--refresh` updates the cached data snapshot and the manifest.

## When to refresh — quarterly, after the GDP release

The index is driven by the **output gap** and the **equity gap**. The binding data are
**quarterly**: real GDP and BIS credit (CPI and share prices update monthly, but equity
alone rarely flips the verdict). Statistics Canada publishes quarterly GDP roughly **two
months after quarter-end**, so refresh on about this cadence:

| Quarter ends | Refresh around |
|--------------|----------------|
| Mar 31       | early June      |
| Jun 30       | early September |
| Sep 30       | early December  |
| Dec 31       | early March     |

Refreshing more often than quarterly mostly recomputes the same result.

## What "up to date" looks like

After a refresh, check `data/raw/manifest.json`. The `pulled_at` field is your **data
vintage** — cite it with any result ("as of <date>"). Each series lists its `last_date`.
A healthy snapshot has:

- `real_gdp` — last_date within ~1 quarter of today (drives the output gap)
- `real_residential_property`, `total_credit_level` — within ~1 quarter
- `share_prices_nominal` — within ~1 month
- `cpi_statcan` — within ~1 month (the deflator; sourced from StatCan, released ~3 weeks
  after month-end). The FRED `cpi_*` series are kept only as a cross-check and lag more.

Quick check:

```bash
.venv/bin/python -c "import json;m=json.load(open('data/raw/manifest.json'));\
print('vintage',m['pulled_at']);\
[print(f\"{k:28s} {v['last_date']}\") for k,v in m['series'].items()]"
```

## Known data limitations

- **CPI deflator = StatCan (resolved).** The deflator is `cpi_statcan` (StatCan vector
  v41690973, CPI all-items, monthly, 2002=100), which runs to the most recent month and is
  fetched by the same `--refresh`. This closes the old lag where FRED's CPI ended ~2025Q1
  while share prices ran to ~2026Q2. FRED's CPI is a rebased copy of this same StatCan data,
  so we use StatCan wholesale (no splice seam). The FRED `cpi_*` series remain cached only
  as a cross-check.
- **LTDR (loan-to-deposit ratio)** — dropped from scope by decision. It has no clean FRED
  source (would need StatCan chartered-bank loans/deposits) and is not part of the index,
  only a dashboard extra. Not fetched.
- **Index is GDP-anchored.** Even with current CPI, the overheating *index* only advances
  when new quarterly **GDP** lands (output-gap component). Fresh CPI/equity make the equity
  side current, but the headline index date tracks the latest GDP quarter.
- **Revisions.** GDP is revised for several quarters after first release. Because the
  real-time (one-sided) filter is endpoint-sensitive, a verdict sitting near a threshold
  can wobble between refreshes for revision reasons alone. Treat a fresh near-threshold
  reading as indicative; glance at it rather than trust it blindly.

## If a refresh stalls

FRED throttles bursts of requests: a throttled request hangs until it times out.
`fetch_data.py` retries and spaces requests, but if a refresh stalls, wait a minute and
re-run — cached series are skipped, so it resumes where it left off (only `--refresh`
forces a full re-pull). Network egress in this environment goes through `curl`, which the
fetcher shells out to.

## Adding or changing a series

Edit the `SERIES` dict at the top of `fetch_data.py` (label → FRED id + description),
then run `--refresh`. `python fetch_data.py --list` prints the current configuration.

## Data sources (FRED ids)

| Label | FRED id | Series |
|-------|---------|--------|
| real_gdp | NGDPRSAXDCCAQ | Real GDP, Canada, SA, quarterly |
| share_prices_nominal | SPASTT01CAQ661N | Share prices, Canada, index |
| cpi_statcan | StatCan v41690973 | CPI all items, monthly, 2002=100 — **deflator used** |
| cpi_quarterly | CANCPIALLQINMEI | CPI all items, quarterly (FRED, cross-check only) |
| cpi_monthly | CANCPIALLMINMEI | CPI all items, monthly (FRED, cross-check only) |
| total_credit_level | CRDQCAAPABIS | Total credit to private non-financial sector (level) |
| total_credit_pct_gdp | QCAPAM770A | Total credit, % of GDP |
| bank_credit_pct_gdp | QCAPBM770A | Bank credit, % of GDP |
| credit_to_gdp | QCACAM770A | Credit-to-GDP (BIS) |
| real_residential_property | QCAR628BIS | Real residential property prices, index |
