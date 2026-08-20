"""Build the data behind the board page (GitHub Pages site in /docs).

Runs the engine for every country in ALL_COUNTRIES and writes docs/index_data.js —
`const DATA = {...}` — which index.html loads with a plain <script src> tag. Every
.html page in docs/ is hand-edited; this script is the only thing that writes here,
and index_data.js is the only file it writes.

    PYTHONPATH=/home/ethan13/financial-cycles python docs/build_overview.py

Reads:  data/raw/manifest.json          (per-country vintage)
Writes: docs/index_data.js              (the board's data payload)
"""
from __future__ import annotations

import json
from pathlib import Path

from engine.config import ALL_COUNTRIES, AM_METHOD
from engine.run import run

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(__file__).resolve().parent  # the docs/ folder GitHub Pages serves
OUT_JS = SITE / "index_data.js"


def _series(res, col):
    """One-sided gap series as [{q, v}] over its defined span (rounded %)."""
    s = res[col].dropna()
    return [{"q": str(q), "v": round(float(v), 2)} for q, v in s.items()]


def _country(name, cfg, vintages):
    res = run(cfg)
    scored = res.dropna(subset=["OI"])
    last, q = scored.iloc[-1], str(scored.index[-1])
    oi_hist = [{"q": str(i), "oi": round(float(r["OI"]), 3),
                "fe": int(r["flag_equity"]), "fg": int(r["flag_gdp"])}
               for i, r in scored.iterrows()]
    return {
        "name": name,
        "vintage": vintages.get(name, ""),
        "latest": {"q": q, "oi": round(float(last["OI"]), 3),
                   "eq": round(float(last["gap_1s_equity"]), 2),
                   "gd": round(float(last["gap_1s_gdp"]), 2),
                   "fe": int(last["flag_equity"]), "fg": int(last["flag_gdp"])},
        "oi_hist": oi_hist,
        "equity": _series(res, "gap_1s_equity"),
        "gdp": _series(res, "gap_1s_gdp"),
    }


def build_payload() -> dict:
    manifest = json.load(open(ROOT / "data" / "raw" / "manifest.json"))
    vintages = {c: d.get("vintage", "")[:10] for c, d in manifest.get("countries", {}).items()}

    countries = [_country(n, c, vintages) for n, c in ALL_COUNTRIES.items()]
    countries.sort(key=lambda c: (-c["latest"]["oi"], c["name"]))  # hottest first

    # Laeven & Valencia (2020) systemic banking-crisis eras -> strip markers
    lv = json.load(open(ROOT / "data" / "reference" / "lv2020_crises.json"))
    for c in countries:
        c["crises"] = lv["crises"].get(c["name"], [])

    # click-a-quarter source links: provider + series id straight from the fetch registry
    import fetch_data
    file_src = {s.file: (s.provider, s.rid)
                for srcs in fetch_data.COUNTRIES.values() for s in srcs}
    # Wikipedia "YYYY in {name}" article naming (articles/differing names)
    wiki = {"United States": "the United States", "United Kingdom": "the United Kingdom",
            "Netherlands": "the Netherlands", "Czech Republic": "the Czech Republic",
            "Slovak Republic": "Slovakia", "Korea": "South Korea"}
    for c in countries:
        cfg = ALL_COUNTRIES[c["name"]]
        links = {}
        for key in ("equity", "gdp"):
            spec = cfg.series.get(key)
            if spec and spec.file in file_src:
                prov, rid = file_src[spec.file]
                if prov in ("fred", "imf_ifs"):  # linkable public series pages
                    links[key] = {"p": prov, "rid": rid}
        c["links"] = links
        c["wiki"] = wiki.get(c["name"], c["name"])

    hot = sum(1 for c in countries if c["latest"]["oi"] > 0)
    return {
        "thresholds": AM_METHOD.thresholds,
        "weights": AM_METHOD.weights,
        "bands": {n: [AM_METHOD.bands[n].low, AM_METHOD.bands[n].high]
                  for n in AM_METHOD.index_components},
        "summary": {"n": len(countries), "hot": hot, "calm": len(countries) - hot},
        "dropped": ["Cyprus", "Malta", "Singapore", "Taiwan"],
        "countries": countries,
    }


def main() -> int:
    data = build_payload()
    OUT_JS.write_text("const DATA=" + json.dumps(data, separators=(",", ":")) + ";\n")
    print(f"wrote {OUT_JS}  ({OUT_JS.stat().st_size:,} bytes)")
    print(f"countries: {data['summary']['n']}  hot: {data['summary']['hot']}  "
          f"calm: {data['summary']['calm']}")
    print("hottest:", ", ".join(f"{c['name']}({c['latest']['oi']})" for c in data["countries"][:7]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
