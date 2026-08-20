"""Harding-Pagan / BBQ turning-point dating - validation only.

NOT on the critical path to the Overheating Index: the operative filter band comes from
Table 2 (AM sample), not from dated cycle lengths. This step exists only to confirm that
Canadian cycle lengths land near the paper's AM averages.

Spec (Claessens, Kose & Terrones 2011a/2012 - the BBQ implementation Chen & Svirydzenka
cite; see CALCULATIONS.md "Harding-Pagan dating"):
  * run on the log-level series (not the filtered cycle, not detrended);
  * peak at t: (f_t-f_{t-2}>0 and f_t-f_{t-1}>0) and (f_{t+2}-f_t<0 and f_{t+1}-f_t<0);
    trough = mirror image  -> a strict local extremum over a +/-2 quarter window;
  * peaks and troughs must alternate (keep the absolute extremum between same-type);
  * minimum phase = 2 quarters; minimum complete cycle = 5 quarters;
  * asset-price exception: waive the 2-quarter min-phase when a 1-quarter decline > 20%.

Validation targets:
  * primary - the paper's AM-GROUP average cycle length (Table 1); the paper reports no
    per-country lengths in the headline table, so "near the AM average" is what justifies
    applying the AM band to Canada;
  * bonus   - the paper's own Canada figures in Appendix 2 (Cycle Properties by Country)
    and Appendix 3, as a sanity cross-check - allowing for their 1960-2014 sample vs our
    current vintage.

Censoring parameters live on MethodConfig (hp_min_phase, hp_min_cycle,
hp_asset_decline_waiver).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import MethodConfig

_K = 2  # quarterly window half-width (Bry-Boschan quarterly)

# Which index/dashboard series are asset prices (the min-phase waiver applies to them).
ASSET_PRICE = {"equity", "property"}

# Paper Table 1, AM-group average cycle length (years) - the primary validation target.
AM_CYCLE_LEN_YEARS = {"equity": 3.8, "gdp": 6.7, "credit": 7.1, "property": 5.2}


def _candidates(v: np.ndarray) -> list[list]:
    """Strict local extrema over a +/-2 window -> ordered [pos, kind] list."""
    tps: list[list] = []
    for t in range(_K, len(v) - _K):
        if v[t] > v[t - 1] and v[t] > v[t - 2] and v[t] > v[t + 1] and v[t] > v[t + 2]:
            tps.append([t, "peak"])
        elif v[t] < v[t - 1] and v[t] < v[t - 2] and v[t] < v[t + 1] and v[t] < v[t + 2]:
            tps.append([t, "trough"])
    return tps


def _alternate(tps: list[list], v: np.ndarray) -> list[list]:
    """Force alternation: among consecutive same-type extrema keep the absolute one."""
    kept: list[list] = []
    for t, kind in tps:
        if kept and kept[-1][1] == kind:
            prev = kept[-1][0]
            more_extreme = v[t] > v[prev] if kind == "peak" else v[t] < v[prev]
            if more_extreme:
                kept[-1] = [t, kind]
        else:
            kept.append([t, kind])
    return kept


def _waived(v: np.ndarray, i: int, ki: str, j: int, kj: str,
            is_asset: bool, waiver: float) -> bool:
    """Asset-price exception: a 1-quarter contraction (peak->trough) losing > waiver."""
    if not is_asset or ki != "peak" or kj != "trough":
        return False
    return (np.exp(v[j] - v[i]) - 1.0) < -waiver   # level decline exceeds `waiver`


def _censor(tps: list[list], v: np.ndarray, min_phase: int, min_cycle: int,
            is_asset: bool, waiver: float) -> list[list]:
    """Apply alternation + minimum phase/cycle censoring, iterating to convergence."""
    tps = _alternate(tps, v)
    while True:
        removed = False

        # Minimum phase: adjacent (opposite-type) turning points must be >= min_phase apart.
        for k in range(len(tps) - 1):
            (i, ki), (j, kj) = tps[k], tps[k + 1]
            if j - i < min_phase and not _waived(v, i, ki, j, kj, is_asset, waiver):
                del tps[k:k + 2]          # drop the too-short blip (both endpoints)
                tps = _alternate(tps, v)
                removed = True
                break
        if removed:
            continue

        # Minimum complete cycle: same-type turning points must be >= min_cycle apart.
        for k in range(len(tps) - 2):
            (i, ki), (j, _) = tps[k], tps[k + 2]
            if j - i < min_cycle:
                keep_first = (v[i] > v[j]) if ki == "peak" else (v[i] < v[j])
                if keep_first:
                    del tps[k + 1:k + 3]  # keep the more extreme (k); drop middle + k+2
                else:
                    del tps[k:k + 2]      # drop k + middle; keep the more extreme (k+2)
                tps = _alternate(tps, v)
                removed = True
                break
        if not removed:
            break
    return tps


def date_turning_points(log_level: pd.Series, method: MethodConfig,
                        is_asset_price: bool = False) -> pd.DataFrame:
    """Dated peaks/troughs for one log-level series (quarterly PeriodIndex).

    Columns:
      kind          - "peak" / "trough"
      log_level     - f at the turning point
      amplitude_pct - signed % move of the phase ENDING at this turning point,
                      100*(exp(f_t - f_prev) - 1) (paper Appendix "amplitude"); NaN first row
      small_swing   - our diagnostic flag (see below); only if hp_small_swing_frac is set
      note          - human message for flagged rows, "" otherwise

    The small-swing flag is a DIAGNOSTIC, not a censoring rule: no turning point is removed,
    so the dating stays faithful to Claessens' duration-only rules. It just marks swings
    whose |amplitude| < frac x the series' median swing (frac = hp_small_swing_frac), which
    is why our cycle counts can exceed the paper's - the extra cycles are the flagged wiggles.
    """
    y = log_level.dropna()
    v = y.to_numpy(float)
    tps = _censor(_candidates(v), v, method.hp_min_phase, method.hp_min_cycle,
                  is_asset_price, method.hp_asset_decline_waiver)
    vals = [v[t] for t, _ in tps]
    out = pd.DataFrame(
        {"kind": [k for _, k in tps], "log_level": vals},
        index=pd.PeriodIndex([y.index[t] for t, _ in tps], freq="Q", name="date"),
    )
    # Amplitude of the phase ending at each turning point (signed %), paper-Appendix style.
    amp = [float("nan")] + [100.0 * (np.exp(vals[k] - vals[k - 1]) - 1.0)
                            for k in range(1, len(vals))]
    out["amplitude_pct"] = amp

    frac = method.hp_small_swing_frac
    if frac is not None and len(out) > 1:
        median_abs = float(np.nanmedian(np.abs(out["amplitude_pct"].to_numpy())))
        threshold = frac * median_abs
        small = out["amplitude_pct"].abs() < threshold        # NaN first row -> False
        out["small_swing"] = small
        out["note"] = [
            (f"Possible small swing: {abs(a):.1f}% move vs series median "
             f"{median_abs:.1f}% (below {frac:.2f}x-median flag)") if s else ""
            for a, s in zip(out["amplitude_pct"], small)
        ]
    return out


def cycle_summary(tp: pd.DataFrame) -> dict:
    """Cycle-length stats from dated turning points (paper eq 3: L = up + down)."""
    ordinals = tp.index.asi8            # quarterly ordinals: +1 per quarter
    kinds = tp["kind"].to_numpy()
    ups, downs = [], []
    for k in range(len(tp) - 1):
        dur = int(ordinals[k + 1] - ordinals[k])
        (ups if kinds[k] == "trough" else downs).append(dur)   # trough->peak up, peak->trough down
    avg_up = float(np.mean(ups)) if ups else float("nan")
    avg_down = float(np.mean(downs)) if downs else float("nan")
    length_q = avg_up + avg_down
    return {
        "n_peaks": int((kinds == "peak").sum()),
        "n_troughs": int((kinds == "trough").sum()),
        "avg_upswing_q": avg_up,
        "avg_downswing_q": avg_down,
        "avg_cycle_len_q": length_q,
        "avg_cycle_len_yr": length_q / 4.0,
    }


def validate(country=None, method: MethodConfig | None = None) -> pd.DataFrame:
    """Date every Canadian series and compare its cycle length to the AM average."""
    from .config import AM_METHOD, CANADA
    from .data import prepare
    country = country or CANADA
    method = method or AM_METHOD

    data = prepare(country)
    rows = []
    for name in list(method.index_components) + list(method.dashboard_components):
        tp = date_turning_points(data[f"log_{name}"], method, name in ASSET_PRICE)
        s = cycle_summary(tp)
        n_small = int(tp["small_swing"].sum()) if "small_swing" in tp else 0
        rows.append({
            "series": name,
            "n_cycles": min(s["n_peaks"], s["n_troughs"]),
            "small_swings": n_small,
            "up_q": round(s["avg_upswing_q"], 1),
            "down_q": round(s["avg_downswing_q"], 1),
            "len_yr (Canada)": round(s["avg_cycle_len_yr"], 1),
            "len_yr (AM avg)": AM_CYCLE_LEN_YEARS.get(name),
        })
    return pd.DataFrame(rows).set_index("series")


def main() -> int:
    tbl = validate()
    print("Harding-Pagan / BBQ cycle lengths - Canada vs paper AM average (Table 1)\n")
    print(tbl.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
