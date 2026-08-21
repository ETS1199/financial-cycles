"""Run the AM Overheating Index engine for one country.

Wires the pipeline: config -> data prep (Steps 1-3) -> CF filter (Steps 4-5) ->
gaps / flags / index (Steps 6-8).

    python -m engine.run          # run Canada with the AM method

``run()`` returns a tidy quarterly results frame; ``main()`` prints the latest reading.
"""
from __future__ import annotations

import pandas as pd

from . import filters, index
from .config import AM_METHOD, CANADA, CountryConfig, MethodConfig
from .data import prepare


def run(country: CountryConfig = CANADA, method: MethodConfig = AM_METHOD) -> pd.DataFrame:
    data = prepare(country)  # Steps 1-3

    # Steps 4-6: two-sided and one-sided percent gaps for every series. Only process
    # components this country actually supplies (a country may omit dashboard series, or
    # have a series dropped for lack of coverage); the index components are still required.
    all_components = list(method.index_components) + list(method.dashboard_components)
    components = [c for c in all_components if f"log_{c}" in data.columns]
    missing_core = [c for c in method.index_components if c not in components]
    if missing_core:
        raise ValueError(f"{country.name}: missing required index series {missing_core}")
    result: dict[str, pd.Series] = {}
    for name in components:
        series = data[f"log_{name}"].dropna()
        band = method.bands[name]
        c1 = filters.one_sided(series, band, method.cf_drift)
        # Display-only trim: the one-sided read is blind until the window covers the band's
        # longest cycle (p_u = band.high), so blank those early quarters to keep artifacts
        # from flagging. This lives in the presentation layer, not the filter (decision:
        # one-sided no-warmup - the trim is our display choice, not part of the method).
        c1.iloc[: band.high] = float("nan")
        result[f"gap_2s_{name}"] = index.gap(filters.two_sided(series, band, method.cf_drift))
        result[f"gap_1s_{name}"] = index.gap(c1)
    res = pd.DataFrame(result).sort_index()

    # Steps 7-8: flags + Overheating Index on the one-sided gaps of the index components.
    gap_1s = res[[f"gap_1s_{n}" for n in method.index_components]].copy()
    gap_1s.columns = list(method.index_components)
    flag_df = index.flags(gap_1s, method)
    for n in method.index_components:
        res[f"flag_{n}"] = flag_df[n]
    res["OI"] = index.overheating_index(flag_df, method)

    res.attrs["country"] = country.name
    return res


def main() -> int:
    res = run()
    scored = res.dropna(subset=["OI"])
    print(f"AM Overheating Index - {res.attrs['country']}")
    print(f"quarters computed: {res.index[0]} .. {res.index[-1]}  (n={len(res)})")
    print(f"quarters with OI:  {scored.index[0]} .. {scored.index[-1]}  (n={len(scored)})")
    print("\nlatest scored quarter:")
    print(scored.iloc[-1].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
