# Canada Financial-Cycle Overheating — Roadmap

Applying the Advanced-Market (AM) methodology of Chen & Svirydzenka (2021),
*"Financial Cycles – Early Warning Indicators of Banking Crises?"* (IMF WP/21/116),
to current Canadian data to assess where Canada sits in its financial cycle.

> **Status (2026-08):** Canada complete and published (Phases 1–4). The engine has since been
> **extended to the full AM country set — 30 of 34 built** (see *Phase 5* below). Presentation
> for the multi-country set is the current work.

## Goal

Reproduce the paper's **AM Overheating Index** for Canada on live data, surrounded by a
dashboard of the other AM indicators, and display the result on a self-contained webpage.

## The target metric — AM Overheating Index (eq. 8)

```
OI_AM = w1 * I_equity + w2 * I_GDP
```

- `I_equity` = 1 if the real equity-price gap breaches its threshold, else 0
- `I_GDP`    = 1 if the output gap breaches its threshold, else 0
- Weights (Table 5): equity 0.6 (norm. 49.7%), GDP 0.6 (norm. 50.3%)
- Index takes values 0 (calm), ~0.5 (one overheating), 1 (both overheating)

Crisis-calibrated AM thresholds (Table 5, "percent deviation from trend"):

| Indicator            | Threshold |
|----------------------|-----------|
| Real equity-price gap| > 6.7%    |
| Output gap           | > 1.3%    |

These two are the paper's best AM leading indicators (equity + output gap), explicitly
**not** credit-to-GDP.

## Methodology chain (must match the paper so thresholds stay valid)

1. Assemble quarterly, real, seasonally-adjusted data: real GDP; real equity prices
   (share-price index / CPI).
2. Date cycles with the Harding–Pagan turning-point algorithm (validation vs. paper's
   AM cycle lengths).
3. Extract cyclical gaps with the Christiano–Fitzgerald band-pass filter using the
   **AM-sample frequency band (Table 2)**: equity 8–22 quarters, GDP 3–51 quarters.
   - One-sided filter -> real-time "where are we now" (headline).
   - Two-sided filter -> historical/structural view (backtest).
4. Flag each indicator vs. its threshold; aggregate into `OI_AM`.
5. Interpret against Canada's own history and backtest vs. 2008–09.

## Locked decisions

- **Scope:** AM index (equity + GDP) **+ AM dashboard** (credit, property, inflation) as
  supporting context. LTDR dropped (no clean data source; not an index component).
- **Output gap:** derive with the paper's filter **and** cross-check vs. Bank of
  Canada / IMF published gap.
- **Filter band:** use the paper's AM-sample band (keeps thresholds comparable);
  Canada-specific length shown only as robustness.
- **Headline:** one-sided (real-time) filter; two-sided shown as context.

## Known caveats

- Table 5 publishes AM thresholds only for equity (6.7%) and GDP (1.3%). Dashboard
  extras (credit, property, inflation) have **no paper-calibrated AM threshold** —
  shown as directional context only.
- One-sided filters are endpoint-sensitive; the latest few quarters get revised. The
  current read is indicative, not precise.
- Deriving AM thresholds for the dashboard extras would require replicating the full
  34-country crisis loss-function — out of scope, flagged as a possible extension.

## Data inventory (FRED, validated reachable)

| Series                | FRED ID           | Use                     |
|-----------------------|-------------------|-------------------------|
| Real GDP, Canada      | NGDPRSAXDCCAQ     | output gap input        |
| Share prices, Canada  | SPASTT01CAQ661N   | equity (deflate by CPI) |
| CPI, Canada (deflator)| StatCan v41690973 | monthly, to latest month (closes the lag) |
| Total credit (level)  | CRDQCAAPABIS      | dashboard: real credit |
| Credit-to-GDP / % GDP | QCACAM770A / QCAPAM770A / QCAPBM770A | dashboard |
| Real residential property | QCAR628BIS    | dashboard: property |

## Phases

- **Phase 1 — Data:** install stack; pull & clean series; deflate equity; close CPI tail.
- **Phase 2 — Engine:** Harding–Pagan dating + CF band-pass filter; validate cycle lengths.
- **Phase 3 — Index:** apply thresholds, build `OI_AM`, backtest 2008–09, cross-check gap.
- **Phase 4 — Display:** self-contained webpage — verdict gauge, gap charts with threshold
  lines and shaded overheating zones, index history, latest-values table, methodology.

## Phase 5 — Advanced-Market expansion (Canada → all AMs)

Extend the same engine (`run(country_config, method_config)`) to the paper's 34 AM countries.
The **method is unchanged** (AM bands, thresholds, weights) so every country's gaps stay
comparable to the paper's calibrated thresholds; only the data sources differ per country.

**Status: 30 of 34 built.** All majors covered (US, UK, Germany, France, Japan, Korea,
Australia, Switzerland, Italy, Netherlands, Spain, Hong Kong, …). Currently 7 flag a marker —
Denmark (output gap) and Canada, Slovenia, Czech Republic, Luxembourg, Spain, Greece (equity);
the other 23 read calm. Hong Kong (added 2026-08-18) is sourced entirely from IMF IFS — equity
is the IFS share-price index `Q.HK.FPE_IX`, a documented proxy for OECD `SPASTT01` (history
from 1996, the shortest in the set; ~1yr IMF lag like other IFS-sourced countries).

**Dropped (4)** — no comparable share-price series in any open API surveyed (FRED/OECD
`SPASTT01`, IMF IFS `FPE_IX` current, Stooq — anti-bot walled): Cyprus, Malta, Singapore,
Taiwan. Singapore's IFS equity series ends 2017; GDP/CPI are ready, so it unlocks if an STI
source (MAS/SingStat) checks out. Cyprus/Malta equity would need national-exchange scraping
for short (~1996+) thin series — low value. Taiwan needs all-national sources (TWSE/DGBAS).

### Data sourcing (per country, mirrors Canada's recipe)

Equity + real GDP come from FRED where available; CPI comes from a **national/current source**
because FRED's OECD CPI lags badly (~1 yr+). Adapters built (all in `fetch_data.py`, table/registry
driven; one command — `python fetch_data.py --refresh` — refreshes everything):

| Provider | Serves | Notes |
|----------|--------|-------|
| **FRED API** (`api.stlouisfed.org`) | equity, GDP, some CPI (US) | **Must use the API + free key**, not the `fredgraph.csv` chart endpoint (WAF-blocks datacenter IPs). Key in gitignored `.fred_api_key`. |
| **Eurostat** (HICP + `namq_10_gdp`) | EU/EEA GDP + CPI | Open, no key; one source covers the whole EU/EEA bloc (incl. Switzerland GDP as EFTA). |
| **ONS** (UK) | UK CPI | Open; `www.ons.gov.uk/…/data` (the old `api.ons.gov.uk` is dead). Current. |
| **ABS** (Australia) | AU CPI | Open SDMX; current. |
| **StatCan / Bank of Canada** | CA CPI / output-gap cross-check | Canada only (Phases 1–3). |
| **IMF IFS** (via DBnomics) | CPI (and GDP) for non-EU markets; all three series for Hong Kong (equity = `FPE_IX` share-price index, SPASTT01 proxy) | Open, no key; uniform across countries; lags ~1 yr. Handles monthly & quarterly. |

### Architecture / decisions (Phase 5)

- **Table-driven onboarding.** EU bloc generated from one `(name, iso, geo)` table in both
  `fetch_data.py` and `engine/config.py`; `ALL_COUNTRIES` is the master registry.
- **Per-country data vintage** in `data/raw/manifest.json` — refreshing one country never
  bumps another's published vintage (protects Canada's pinned page vintage).
- **Ragged edge / currency.** FRED-CPI (US) + ONS (UK) + ABS (AU) + StatCan (CA) are current to
  2026Q1/Q2; EU (Eurostat) reads ~2025Q4 in this sandbox (snapshot; current in production) and
  IMF-sourced countries ~2025Q2–Q3 (IMF release lag). The index date is anchored to the latest
  quarter where both equity and output flags exist.
- **Coverage caveat.** The small-market equity flags sit on thin share-price indices and a
  volatile one-sided filter — read skeptically (flag, don't over-interpret).

### Phase 5 remaining

- **Presentation (current work):** the multi-country board is the flagship. **Site restructured
  2026-08-19 for GitHub Pages** (`docs/`, servable straight from the repo): every `.html` is
  hand-edited (`index.html` board + drill-in, `about.html`, `methodology.html`,
  `references.html`, shared `styles.css`); the data lives in generated `index_data.js`
  (`const DATA={…}`), the only file `docs/build_overview.py` writes. No template step.
  The claude.ai artifact is now a legacy preview. The standalone Canada "Looking Back" page was **retired
  2026-08-19** (Canada is on the board; its build files were moved out of the repo by the user).
  Possible future: fold a "Canada deep-dive" (BoC cross-check, two-sided view, reliability) into
  the board's Canada detail view.
- **Clickable hot quarters → historical context (idea, 2026-08-18).** Clicking an overheating
  quarter in a country's heat-strip surfaces links/context explaining what was happening there
  at that time (e.g. Greece's 4-quarter hot streak). Implementation tiers, easiest first:
  1. *Provider deep links — DONE 2026-08-18.* Clicking any quarter in the heat-strip opens a
     popover (#qmenu) with: FRED share-price / GDP series pages windowed ±3 yrs on the clicked
     quarter (`?cosd=/&coed=`); DBnomics IMF-IFS series pages where the source isn't FRED
     (Hong Kong, IL/NZ GDP); a Wikipedia "YYYY in {Country}" link (article-name map in
     build_overview.py: US/UK/NL/CZ take "the", Slovak Republic→Slovakia, Korea→South Korea);
     and the L&V crisis-era note when the quarter falls in one. Provider+rid come from the
     fetch_data registry — new countries inherit links automatically. Eurostat-sourced GDP has
     no per-country deep link (omitted rather than linked generically).
  2. *Laeven–Valencia crisis overlay — DONE 2026-08-18.* Dates parsed from the published
     dataset (L&V 2020, IMF Economic Review 68 — Springer supplementary xlsx; the IMF-hosted
     WP PDF is bot-blocked) into `data/reference/lv2020_crises.json` with `truncated` (fn 7/,
     5-yr duration cap) and `borderline` (fn 8/) flags. Rendered as a dark underline beneath
     the heat-strip cells (truncated ends trail off in a gradient fade), in the tooltip, the
     legend, and the References note. 26 of 30 countries have episodes; CA/AU/HK/NZ have none.
  3. *Generated episode explainers (later):* per-quarter narrative on click via the artifact
     runtime's AI capability — needs a capability check and design pass; defer until 1–2 prove out.
  External links are viable in the artifact (CSP blocks external fetches, not link navigation).
- **Display the two-sided gaps (queued 2026-08-19).** The engine already computes `gap_2s_*`
  for every country on every run; the board build currently discards them. Plan: ship both
  series in `index_data.js` and add a real-time / hindsight toggle on the two country detail
  charts — a direct illustration of the revision behavior the Methodology page now explains
  (one-sided readings converging to the two-sided line). Payload roughly doubles per-country
  gap data (~30 → ~60 numbers per series per country; fine). Natural companion to a future
  "Canada deep-dive" (BoC cross-check + reliability stats, which use the two-sided flags as
  the answer key).
- **Restore a "How to read it" caveats section (removed 2026-08-19, revisit when the site has
  more to say).** Deleted from About as premature; the substance lives on in Methodology's
  *Limits of the calibration*. What it covered, for rebuilding later: (1) not a crisis forecast —
  thresholds calibrated on *other* economies' crises; (2) real-time readings are muted;
  (3) small markets sit on thin share-price indices — read flags skeptically; (4) the
  calibration is frozen at 2014.
  **Correction to carry forward:** the old bullet said newest quarters "get revised." That is
  wrong for this site. `one_sided` is recursive (`cffilter(v[:t+1])`, last point), so a
  quarter's value depends only on data up to that quarter and never moves — verified: re-running
  Canada's equity gap with 4 fewer quarters left all 277 overlapping values identical to 1e-12.
  The true point is real-time vs hindsight *for the same quarter*: Canada 2024Q3 read +1.1% at
  the time, but sits at −5.6% with today's data (a sign flip); the two converge to identical at
  the final observation. Source-data revisions (agencies restating GDP/CPI) are a separate,
  genuine channel — don't conflate them.
- **Optional currency upgrades:** national CPI for the IMF-lagged countries (e.g. e-Stat for Japan).
- **Optional:** revisit the 4 dropped — Singapore first (only equity missing; try MAS/SingStat
  for the STI), then Taiwan/Cyprus/Malta via national sources if ever worth it.

## Phase 6 — Emerging-market track (queued 2026-08-19, announced on the site)

The paper has a parallel EM track: 25 EM countries with their own Table 2 frequency bands and
Table 5 thresholds/weights (EM cycles are shorter and larger-amplitude, so AM constants must NOT
be reused). Same engine, second MethodConfig (`EM_METHOD`) + per-country data sourcing (expect
more IMF IFS / national sources, fewer FRED series). The board's coverage note now says EMs are
"planned for a future update," so this is a public commitment — keep or remove that line
deliberately.
