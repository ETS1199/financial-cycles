"""Output-gap cross-check (Phase 3) - our filtered GDP gap vs external official gaps.

Validation only, off the OI path. Compares our CF band-pass GDP gap (two-sided and
one-sided) against published output-gap series - for Canada, the Bank of Canada's official
quarterly estimates (Current MPR, Integrated Framework, Extended Multivariate Filter).

Our gap is a band-pass *cyclical deviation*; the BoC gap is a *deviation from potential*.
They are conceptually different constructions, so we expect strong positive co-movement
rather than equality. Reported per reference series over the overlapping window:
  * corr_two_sided - correlation of our hindsight gap with the reference
  * corr_one_sided - correlation of our real-time gap (weaker, as the paper notes)
  * our_sd / ref_sd - amplitude comparison
"""
from __future__ import annotations

import pandas as pd

from .config import AM_METHOD, CANADA, CountryConfig, MethodConfig
from .data import _read, _to_quarterly
from .run import run


def crosscheck(country: CountryConfig = CANADA, method: MethodConfig = AM_METHOD,
               results: pd.DataFrame | None = None) -> pd.DataFrame:
    res = results if results is not None else run(country, method)
    ours2 = res["gap_2s_gdp"].dropna()
    ours1 = res["gap_1s_gdp"].dropna()

    rows = []
    for name, spec in country.crosscheck_gaps.items():
        ext = _to_quarterly(_read(spec), spec.freq)                  # already a % gap
        j2 = pd.concat([ours2, ext], axis=1, join="inner").dropna()
        j1 = pd.concat([ours1, ext], axis=1, join="inner").dropna()
        rows.append({
            "reference": name,
            "overlap_q": len(j2),
            "corr_two_sided": round(j2.iloc[:, 0].corr(j2.iloc[:, 1]), 3),
            "corr_one_sided": round(j1.iloc[:, 0].corr(j1.iloc[:, 1]), 3),
            "our_sd": round(j2.iloc[:, 0].std(), 2),
            "ref_sd": round(j2.iloc[:, 1].std(), 2),
        })
    return pd.DataFrame(rows).set_index("reference")


def realtime_reliability(country: CountryConfig = CANADA, method: MethodConfig = AM_METHOD,
                         results: pd.DataFrame | None = None) -> pd.DataFrame:
    """How often the real-time (one-sided) call matched the final (two-sided) verdict.

    For each index component, compares the real-time flag to the hindsight flag over every
    quarter both are defined: agreement rate, false alarms (flagged live, later revised
    away), and misses (final says hot, real time missed it).
    """
    from .index import flags

    res = results if results is not None else run(country, method)
    comps = list(method.index_components)
    g2 = res[[f"gap_2s_{n}" for n in comps]].copy(); g2.columns = comps
    g1 = res[[f"gap_1s_{n}" for n in comps]].copy(); g1.columns = comps
    f2, f1 = flags(g2, method), flags(g1, method)

    rows = []
    for n in comps:
        both = f1[n].notna() & f2[n].notna()
        a, b = f1[n][both], f2[n][both]
        rows.append({
            "component": n,
            "quarters": int(both.sum()),
            "agreement": round(float((a == b).mean()), 3),
            "false_alarms": int(((a == 1) & (b == 0)).sum()),   # flagged live, revised away
            "misses": int(((a == 0) & (b == 1)).sum()),         # final hot, missed live
        })
    return pd.DataFrame(rows).set_index("component")


def main() -> int:
    print("Output-gap cross-check - our filtered GDP gap vs Bank of Canada official gap\n")
    print(crosscheck().to_string())
    print("\nReal-time reliability - one-sided (live) vs two-sided (hindsight) flags\n")
    print(realtime_reliability().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
