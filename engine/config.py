"""Configuration for the AM Overheating Index engine.

Every run is driven by two configs (CALCULATIONS.md, "Extensibility / architecture"):

  MethodConfig  - the paper's shared method, identical across all Advanced Markets so
                  gaps stay comparable to the calibrated thresholds: AM frequency bands
                  (Table 2), thresholds & weights (Table 5), the CF drift setting, and
                  the Harding-Pagan censoring parameters.
  CountryConfig - which raw series feed the engine for one country. Swap this alone to
                  apply the engine to another AM. Canada is the first instance.

Values are sourced from Chen & Svirydzenka (2021), IMF WP/21/116:
  * bands      - Table 2 (AM sample)
  * thresholds - Table 5 (AM), percent deviation from trend
  * weights    - Table 5 (AM), published normalized weights. The raw weights print as
                 0.6/0.6 (rounded); the operative published normalized weights are
                 49.7 / 50.3, which is what we use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Pinned raw data vintage (see data/raw/manifest.json).
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


@dataclass(frozen=True)
class Band:
    """CF pass-band in quarters: keep oscillations with period in [low, high]."""
    low: int    # p_l, minimum period  (statsmodels `low`)
    high: int   # p_u, maximum period  (statsmodels `high`)


@dataclass(frozen=True)
class SeriesSpec:
    """One raw input series and how to turn it real."""
    file: str        # filename in data/raw
    column: str      # value column in that CSV
    freq: str        # 'Q' quarterly, or 'M' monthly (CPI) -> aggregated to Q
    deflate: bool    # divide by quarterly CPI to get a real series? (Step 2)


@dataclass(frozen=True)
class MethodConfig:
    bands: dict[str, Band]
    thresholds: dict[str, float]           # % dev from trend; index components only
    weights: dict[str, float]              # published normalized OI weights (Table 5)
    index_components: tuple[str, ...]      # feed the Overheating Index
    dashboard_components: tuple[str, ...]  # context only, no calibrated threshold
    cf_drift: bool = True
    # Harding-Pagan / BBQ censoring (Claessens et al.; see dating.py)
    hp_min_phase: int = 2                  # quarters
    hp_min_cycle: int = 5                  # quarters
    hp_asset_decline_waiver: float = 0.20  # waive min-phase if a 1-quarter drop > 20%
    # Small-swing diagnostic (OUR annotation, NOT a censoring rule): flag a swing whose
    # |amplitude| < frac x that series' median swing. None disables. See CALCULATIONS.md.
    hp_small_swing_frac: float | None = 0.25


@dataclass(frozen=True)
class CountryConfig:
    name: str
    cpi: SeriesSpec                # monthly CPI deflator (Step 1)
    series: dict[str, SeriesSpec]  # logical name -> spec
    # External published output-gap series for the Phase-3 GDP-gap cross-check (already in
    # percent, so deflate=False and no logging). Empty = no cross-check for this country.
    crosscheck_gaps: dict[str, SeriesSpec] = field(default_factory=dict)


# ---- The paper's Advanced-Market method (shared across all AMs) -------------
AM_METHOD = MethodConfig(
    bands={
        "equity":   Band(8, 22),   # Table 2 (AM)
        "gdp":      Band(3, 51),
        "credit":   Band(5, 50),   # dashboard
        "property": Band(5, 36),   # dashboard
    },
    thresholds={"equity": 6.7, "gdp": 1.3},    # Table 5 (AM)
    weights={"equity": 0.497, "gdp": 0.503},   # Table 5 (AM), normalized
    index_components=("equity", "gdp"),
    dashboard_components=("credit", "property"),
)


# ---- Canada (first country instance) ---------------------------------------
CANADA = CountryConfig(
    name="Canada",
    cpi=SeriesSpec("cpi_statcan__v41690973.csv", "value", "M", deflate=False),
    series={
        "equity":   SeriesSpec("share_prices_nominal__SPASTT01CAQ661N.csv", "SPASTT01CAQ661N", "Q", deflate=True),
        "gdp":      SeriesSpec("real_gdp__NGDPRSAXDCCAQ.csv",               "NGDPRSAXDCCAQ",   "Q", deflate=False),
        "credit":   SeriesSpec("total_credit_level__CRDQCAAPABIS.csv",      "CRDQCAAPABIS",    "Q", deflate=True),
        "property": SeriesSpec("real_residential_property__QCAR628BIS.csv", "QCAR628BIS",      "Q", deflate=False),
    },
    crosscheck_gaps={
        "BoC Current MPR":          SeriesSpec("boc_output_gap_mpr__INDINF_OUTGAPMPR_Q.csv", "value", "Q", deflate=False),
        "BoC Integrated Framework": SeriesSpec("boc_output_gap_if__INDINF_OUTGAPI_Q.csv",    "value", "Q", deflate=False),
        "BoC Extended MV Filter":   SeriesSpec("boc_output_gap_emvf__INDINF_OUTGAPM_Q.csv",  "value", "Q", deflate=False),
    },
)


# ---- Australia (second country; core pilot) --------------------------------
# Equity & GDP from FRED (files load as-is: FRED CSVs already have observation_date +
# the series id as the value column). CPI from ABS (All groups CPI, Index Numbers,
# quarterly), normalized to observation_date,value in AU__cpi.csv. Credit/property
# (dashboard) and an output-gap cross-check can be added later.
AUSTRALIA = CountryConfig(
    name="Australia",
    cpi=SeriesSpec("AU__cpi.csv", "value", "Q", deflate=False),
    series={
        "equity": SeriesSpec("AU__share_prices_nominal.csv", "SPASTT01AUQ661N", "Q", deflate=True),
        "gdp":    SeriesSpec("AU__real_gdp.csv",             "NGDPRSAXDCAUQ",   "Q", deflate=False),
    },
)


# ---- United States (core pilot) --------------------------------------------
# All three from FRED. CPI = CPIAUCSL (BLS CPI-U, monthly, SA) — current, unlike the
# lagging OECD CPI; only its deviation-from-trend is used, so base year is irrelevant.
UNITED_STATES = CountryConfig(
    name="United States",
    cpi=SeriesSpec("US__cpi.csv", "CPIAUCSL", "M", deflate=False),
    series={
        "equity": SeriesSpec("US__share_prices_nominal.csv", "SPASTT01USQ661N", "Q", deflate=True),
        "gdp":    SeriesSpec("US__real_gdp.csv",             "NGDPRSAXDCUSQ",   "Q", deflate=False),
    },
)


# ---- United Kingdom (equity+GDP from FRED, CPI from ONS) --------------------
UNITED_KINGDOM = CountryConfig(
    name="United Kingdom",
    cpi=SeriesSpec("GB__cpi.csv", "value", "M", deflate=False),
    series={
        "equity": SeriesSpec("GB__share_prices_nominal.csv", "SPASTT01GBQ661N", "Q", deflate=True),
        "gdp":    SeriesSpec("GB__real_gdp.csv",             "NGDPRSAXDCGBQ",   "Q", deflate=False),
    },
)


# ---- Japan (equity+GDP from FRED, CPI from IMF IFS via DBnomics) ------------
# FRED's OECD Japan CPI is dead (stops 2022); IMF IFS is the no-key current-ish source
# (lags ~1yr). e-Stat would be bang-current but needs a registered appId — deferred.
JAPAN = CountryConfig(
    name="Japan",
    cpi=SeriesSpec("JP__cpi.csv", "value", "M", deflate=False),
    series={
        "equity": SeriesSpec("JP__share_prices_nominal.csv", "SPASTT01JPQ661N", "Q", deflate=True),
        "gdp":    SeriesSpec("JP__real_gdp.csv",             "NGDPRSAXDCJPQ",   "Q", deflate=False),
    },
)


# ---- Israel & New Zealand (equity FRED; GDP + CPI from IMF IFS) -------------
# No FRED GDP for either; IMF IFS quarterly real GDP fills in. NZ reports CPI quarterly
# (no monthly IMF series), so its CPI freq is 'Q' rather than 'M'.
ISRAEL = CountryConfig(
    name="Israel",
    cpi=SeriesSpec("IL__cpi.csv", "value", "M", deflate=False),
    series={
        "equity": SeriesSpec("IL__share_prices_nominal.csv", "SPASTT01ILQ661N", "Q", deflate=True),
        "gdp":    SeriesSpec("IL__real_gdp.csv",             "value",           "Q", deflate=False),
    },
)

NEW_ZEALAND = CountryConfig(
    name="New Zealand",
    cpi=SeriesSpec("NZ__cpi.csv", "value", "Q", deflate=False),
    series={
        "equity": SeriesSpec("NZ__share_prices_nominal.csv", "SPASTT01NZQ661N", "Q", deflate=True),
        "gdp":    SeriesSpec("NZ__real_gdp.csv",             "value",           "Q", deflate=False),
    },
)


# ---- Hong Kong (all three series from IMF IFS) ------------------------------
# No FRED/OECD coverage (non-OECD member). Equity = IFS share-price index (FPE_IX),
# a documented proxy for OECD SPASTT01 — both broad national share-price indices.
# Equity starts 1996 (shortest history in the set); IMF lag ~1yr like Japan/Korea/Israel.
HONG_KONG = CountryConfig(
    name="Hong Kong",
    cpi=SeriesSpec("HK__cpi.csv", "value", "M", deflate=False),
    series={
        "equity": SeriesSpec("HK__share_prices_nominal.csv", "value", "Q", deflate=True),
        "gdp":    SeriesSpec("HK__real_gdp.csv",             "value", "Q", deflate=False),
    },
)


# ---- Korea (equity+GDP from FRED, CPI from IMF IFS) ------------------------
KOREA = CountryConfig(
    name="Korea",
    cpi=SeriesSpec("KR__cpi.csv", "value", "M", deflate=False),
    series={
        "equity": SeriesSpec("KR__share_prices_nominal.csv", "SPASTT01KRQ661N", "Q", deflate=True),
        "gdp":    SeriesSpec("KR__real_gdp.csv",             "NGDPRSAXDCKRQ",   "Q", deflate=False),
    },
)


# ---- Switzerland (equity FRED, GDP Eurostat/EFTA, CPI IMF IFS) --------------
# No FRED GDP series for CH; Eurostat covers it as an EFTA member. CPI via IMF IFS.
SWITZERLAND = CountryConfig(
    name="Switzerland",
    cpi=SeriesSpec("CH__cpi.csv", "value", "M", deflate=False),
    series={
        "equity": SeriesSpec("CH__share_prices_nominal.csv", "SPASTT01CHQ661N", "Q", deflate=True),
        "gdp":    SeriesSpec("CH__real_gdp.csv",             "value",           "Q", deflate=False),
    },
)


# ---- EU/EEA advanced-market bloc --------------------------------------------
# Uniform recipe across the bloc: equity from FRED (SPASTT01{iso}), GDP + CPI from Eurostat,
# both normalized to observation_date,value. Cyprus & Malta are excluded (no FRED share-price
# series). File prefix = FRED iso2; the Eurostat geo (Greece = EL) lives in the fetch registry
# (fetch_data.py EU_AM), not here. (display name, FRED iso2 / file prefix).
_EU_AM = [
    ("Austria", "AT"), ("Belgium", "BE"), ("Czech Republic", "CZ"), ("Denmark", "DK"),
    ("Estonia", "EE"), ("Finland", "FI"), ("France", "FR"), ("Germany", "DE"),
    ("Greece", "GR"), ("Ireland", "IE"), ("Italy", "IT"), ("Luxembourg", "LU"),
    ("Netherlands", "NL"), ("Portugal", "PT"), ("Slovak Republic", "SK"), ("Slovenia", "SI"),
    ("Spain", "ES"), ("Sweden", "SE"), ("Iceland", "IS"), ("Norway", "NO"),
]


def _eu_config(name: str, iso: str) -> CountryConfig:
    return CountryConfig(
        name=name,
        cpi=SeriesSpec(f"{iso}__cpi.csv", "value", "M", deflate=False),
        series={
            "equity": SeriesSpec(f"{iso}__share_prices_nominal.csv", f"SPASTT01{iso}Q661N", "Q", deflate=True),
            "gdp":    SeriesSpec(f"{iso}__real_gdp.csv", "value", "Q", deflate=False),
        },
    )


EU_CONFIGS = {name: _eu_config(name, iso) for name, iso in _EU_AM}

# Master registry of every configured country (used to run/build the whole set).
ALL_COUNTRIES: dict[str, CountryConfig] = {
    "Canada": CANADA, "Australia": AUSTRALIA, "United States": UNITED_STATES,
    "United Kingdom": UNITED_KINGDOM, "Japan": JAPAN, "Switzerland": SWITZERLAND,
    "Korea": KOREA, "Israel": ISRAEL, "New Zealand": NEW_ZEALAND, "Hong Kong": HONG_KONG,
    **EU_CONFIGS,
}
