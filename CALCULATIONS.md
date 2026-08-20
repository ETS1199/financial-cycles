# Calculations — AM Overheating Index for Canada

Precise, step-by-step definition of every quantity we compute. Companion to `ROADMAP.md`
(overview) and `REFRESH.md` (data updates). Method follows Chen & Svirydzenka (2021),
IMF WP/21/116, Advanced-Market (AM) track.

## Notation & inputs

| Symbol | Meaning | Source |
|--------|---------|--------|
| `SP_q`   | nominal share-price index, quarter q (period average) | FRED `SPASTT01CAQ661N` |
| `cpi_m`  | CPI all-items, month m (2002=100)                     | StatCan vector `v41690973` |
| `CPI_q`  | quarterly CPI = mean of the 3 months in quarter q     | derived |
| `G_q`    | real GDP, quarter q (SA)                               | FRED `NGDPRSAXDCCAQ` |
| `CR_q`   | total credit to private non-fin sector, level (nominal)| FRED `CRDQCAAPABIS` |
| `PR_q`   | real residential property price index                 | FRED `QCAR628BIS` |

All series are quarterly (monthly CPI is aggregated as below). Everything is worked in
natural logs; gaps are reported in percent.

## Step 1 — quarterly alignment of CPI

```
CPI_q = mean( cpi_m : m in quarter q )          # average of the quarter's 3 months
```

Both `SP_q` and `CPI_q` are period averages, so they line up consistently.

## Step 2 — real (inflation-adjusted) series

```
E_q = SP_q / CPI_q                 # real equity price index
G_q = NGDPRSAXDCCAQ                 # already real, SA — used as-is
CR_real_q = CR_q / CPI_q           # real credit (dashboard only)
PR_q                               # already real — used as-is (dashboard only)
```

(The absolute scale of `E_q` is irrelevant — only its deviation from trend is used.)

## Step 3 — logs

```
e_q = ln(E_q)      g_q = ln(G_q)      cr_q = ln(CR_real_q)      pr_q = ln(PR_q)
```

## Step 4 — band-pass filter (Christiano–Fitzgerald)

Extract the cyclical component with the CF band-pass filter, `drift=True` (series are
trending / I(1)). Frequency band = the paper's **AM-sample** min/max cycle length
(Table 2), in quarters:

| Series | low (p_l) | high (p_h) |
|--------|-----------|------------|
| Equity | 8         | 22         |
| GDP    | 3         | 51         |

(Dashboard series use their own AM bands from Table 2: credit 5–50, property 5–36.)

Harding–Pagan turning-point dating is run on Canada **only to validate** that Canadian
cycle lengths land near the paper's AM averages; the operative filter band is the AM
band above, so our gaps stay comparable to the paper's thresholds.

## Step 5 — two-sided vs one-sided (real-time) gaps

Let `cf(x, p_l, p_h)` return the cyclical component of series `x`.

```
# Two-sided (hindsight): whole sample at once
cycle2s = cf(e, 8, 22)

# One-sided (real-time): recursive replay from the earliest feasible window,
# keep the last point each step.
for t in range(t0, T):        # t0 = smallest window the CF filter accepts
    c = cf(e[0:t+1], 8, 22)
    cycle1s[t] = c[-1]
```

("one-sided" / "two-sided" are the paper's own terms — Chen & Svirydzenka §D.)

The one-sided series is the headline "where are we now" read; two-sided is the cleaner
hindsight view. The newest quarters of the one-sided series are the least certain and get
revised as new data arrives (endpoint sensitivity).

## Step 6 — gaps in percent

```
gap_equity_q = 100 * cycle_equity_q        # ~percent deviation from trend
gap_gdp_q    = 100 * cycle_gdp_q           # = output gap, ~percent
```

(Log-deviation × 100 ≈ percent for the magnitudes involved; exact form is
`100*(exp(cycle)-1)`, negligibly different here.)

## Step 7 — flags (per quarter)

Compare each quarter's **one-sided** gap to the fixed AM threshold (Table 5):

```
I_equity_q = 1 if gap_equity_q > 6.7 else 0
I_gdp_q    = 1 if gap_gdp_q    > 1.3 else 0
```

Thresholds are levels above trend ("too hot"), fixed constants calibrated once by the
paper. Flag is quarter-by-quarter (the threshold value itself came from averaging the 4
quarters before past crises).

## Step 8 — Overheating Index

```
OI_q = w1 * I_equity_q + w2 * I_gdp_q
w1 = 0.497   (equity, normalized)      w2 = 0.503   (GDP, normalized)
```

Possible values: `0` (neither hot), `0.497` (equity only), `0.503` (GDP only),
`1.0` (both). Raw weights are 0.6/0.6 (Table 5); normalized to sum to 1.

## Thresholds & weights (Table 5, AM)

| Indicator | Threshold (% dev. from trend) | Weight | Normalized weight |
|-----------|------------------------------|--------|-------------------|
| Equity    | 6.7                          | 0.6    | 49.7              |
| GDP       | 1.3                          | 0.6    | 50.3              |

Weight = 1 − Type I error (missed crises) − Type II error (false alarms).

## Harding–Pagan dating (validation only)

Run on the **log-level** series `f` (i.e. `e`, `g`, `cr`, `pr` from Step 3), following
Claessens, Kose & Terrones (2011a / 2012) — the "BBQ" implementation of Harding–Pagan
(2002) that Chen & Svirydzenka's dating step cites.

```
Peak at t:   (f_t−f_{t−2}>0 and f_t−f_{t−1}>0) and (f_{t+2}−f_t<0 and f_{t+1}−f_t<0)
Trough at t: mirror image
```

Censoring (Claessens et al., exact):
- peaks and troughs must **alternate** — between two adjacent same-type extrema keep the
  absolute one;
- each **phase** (peak→trough or trough→peak) lasts **≥ 2 quarters**;
- each **complete cycle** (trough→peak→trough) lasts **≥ 5 quarters**;
- **asset-price exception:** the 2-quarter minimum phase is waived when a single-quarter
  decline exceeds **20%** (can bind for equity and property).

Used to confirm Canadian cycle lengths land near the paper's AM averages — **not** to set
the filter band (the operative band is the AM band from Table 2, Step 4).

### Cycle amplitude

For each turning point we also report the **amplitude** of the phase ending there — the
percent level move since the previous turning point (matching the paper's Appendix-2
"amplitude" column):

```
amplitude_t = 100 * ( exp(f_t − f_{t−1}) − 1 )      # signed %; + for upswings, − for downswings
```

### Small-swing diagnostic (ours, not the paper's)

The BBQ rules above are duration-only, so on volatile series (equity most of all) they date
more — and smaller — cycles than the paper reports for Canada (e.g. equity: our ~19 vs the
paper's 11 over 1960–2014). To make that transparent **without deviating from the paper**,
we add a diagnostic flag — it removes nothing, so the dated cycles stay exactly the BBQ
output. A swing is flagged when its amplitude is small **relative to that series' own
swings**:

```
median_abs = median( |amplitude| over all swings in the series )
small_swing_t = |amplitude_t| < frac * median_abs          # frac = hp_small_swing_frac, default 0.25
```

A relative (per-series) threshold is used because swing sizes differ by an order of
magnitude across series (equity swings ~50%, GDP ~2–4%), so no single fixed percent works.
Flagged rows carry a message like *"Possible small swing: 3.1% move vs series median 14.2%
(below 0.25×-median flag)."* The flag is configurable (`hp_small_swing_frac`; `None`
disables) and is **purely informational** — it never changes the turning points, the cycle
lengths, or anything on the Overheating-Index path.

## Output-gap cross-check (validation only)

Sanity-check the filtered **GDP gap** against Canada's official output gap. Source (settled
in Phase 3): the **Bank of Canada**'s quarterly estimates (Valet `INDINF_*`) — all three
published measures: Current MPR, Integrated Framework, Extended Multivariate Filter.

Our gap is a band-pass **cyclical deviation**; the BoC gap is a **deviation from potential**
— different constructions, so we expect strong co-movement, not equality. On the 1981–2026
overlap (181 quarters), our **two-sided** GDP gap correlates **0.87–0.92** with the BoC gaps
(highest with the filter-based EMVF, 0.92); the **one-sided** real-time gap is weaker at
**0.64–0.71**, consistent with the paper's point that real-time filtering has lower signal.
Amplitudes are comparable (sd ≈ 1.8–2.2). Validation only — off the OI path. Implemented in
`engine/crosscheck.py`.

## Engine design decisions (locked)

Settled before building Phase 2. See also the two method decisions above — one-sided filter
has **no warm-up** (Step 5) and Harding–Pagan uses the Claessens BBQ censoring (dating
section).

1. **Per-series sample window.** Filter each series over its **own maximal clean sample**
   (real equity is available from ~1956, real GDP from ~1961), not clipped to a common
   start. The CF trend/drift is estimated per series over its full history — this is what
   the paper does, and it keeps each gap reproducible. Thresholds stay valid because they
   were calibrated on the paper's samples, not on ours.

2. **Ragged edge (latest end).** Each component is computed to its own latest available
   quarter. The composite `OI_q` is published **only for quarters where both the equity and
   GDP flags exist** — i.e. through the latest GDP quarter (currently 2026Q1). Any extra
   equity quarter (e.g. 2026Q2) is shown as component-level context only; GDP is never
   imputed/extrapolated to extend `OI`.

## Extensibility / architecture — other Advanced Markets

**Locked architecture:** the engine is `run(country_config, method_config)`.

- `country_config` = { share-price id, GDP id, CPI source, credit id, property id } (+ any
  country-specific data quirks). Canada is the first instance.
- `method_config` is **shared across all AMs**: the AM bands (Step 4), thresholds and
  weights (Step 7–8), CF `drift=True`, and the Harding–Pagan censoring params.

Applying the engine to another advanced market means swapping only `country_config`; the
shared `method_config` keeps gaps comparable to the paper's thresholds.

## Interpretation / framing (important)

Canada has essentially **no systemic banking crisis** in the Laeven–Valencia database, so:
- thresholds were calibrated on *other* AMs' crises and applied to Canada;
- there is no Canadian crisis to "backtest" against — validation is via sanity checks
  (does the index rise in known booms, e.g. late-1980s, 2000s housing);
- results read as *overheating risk relative to a crisis-calibrated bar*, not a prediction
  that Canada will have a crisis. We report the flags as the paper defines them.

## Open items (F — settle later, do not forget)

- ~~**Output-gap cross-check source:** Bank of Canada vs. IMF WEO~~ — **settled (Phase 3):**
  Bank of Canada quarterly output gap (all three `INDINF_*` measures). See "Output-gap
  cross-check" above.
- **Dashboard deflation details:** confirm real-credit deflation and any dashboard bands;
  dashboard extras are directional context only (no paper-calibrated AM threshold).

## Caveats

- One-sided gaps at the sample edge are uncertain and get revised (see Step 5).
- GDP is revised for several quarters after release; a near-threshold reading can wobble.
- The composite index date is anchored to the latest GDP quarter (currently 2026Q1),
  even though the equity component runs to 2026Q2 (see Engine design decision 2).
