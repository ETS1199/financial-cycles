"""Christiano-Fitzgerald band-pass filter - CALCULATIONS.md Steps 4-5.

Wraps statsmodels' ``cffilter``, which we verified implements CF (1999) eqs (1.2)-(1.4)
plus the drift adjustment exactly.

  two_sided  - filter the whole sample at once (uses past & future; hindsight view).
  one_sided  - the paper's real-time filter (eq 1.4): estimated recursively, at each
               quarter using only data up to that quarter, kept as the last point.

There is deliberately NO warm-up: the recursion starts from the earliest feasible window
(matches Chen & Svirydzenka, who estimate the one-sided filter "recursively... using only
the information available up until that point"). The pre-p_u display trim - where the
window is shorter than the band's longest cycle - is a presentation-layer decision and is
NOT applied here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.filters.cf_filter import cffilter

from .config import Band


def two_sided(x: pd.Series, band: Band, drift: bool = True) -> pd.Series:
    """Full-sample cyclical gap for every quarter."""
    x = x.dropna()
    cycle, _ = cffilter(x.to_numpy(float), low=band.low, high=band.high, drift=drift)
    return pd.Series(np.atleast_1d(cycle), index=x.index)


def one_sided(x: pd.Series, band: Band, drift: bool = True) -> pd.Series:
    """Real-time cyclical gap: recursive replay, keep the last filtered point each step."""
    x = x.dropna()
    v = x.to_numpy(float)
    n = v.size
    out = np.full(n, np.nan)
    # Earliest feasible window is 2 points (the drift adjustment needs n >= 2).
    for t in range(1, n):
        cycle, _ = cffilter(v[: t + 1], low=band.low, high=band.high, drift=drift)
        out[t] = np.atleast_1d(cycle)[-1]
    return pd.Series(out, index=x.index)
