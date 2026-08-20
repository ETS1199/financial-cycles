# Sources & Citations

Running list of every source used, for citation on the final website. Grouped by role.
Links marked (bot-403) return 403 to automated checks but resolve fine in a browser.

## Primary methodology

- **Chen, S. & Svirydzenka, K. (2021). "Financial Cycles – Early Warning Indicators of
  Banking Crises?" IMF Working Paper WP/21/116.**
  The method we replicate (Advanced-Market track). SSRN abstract 3970194.
  - https://ssrn.com/abstract=3970194  (bot-403)
  - Also published on imf.org (search "WP/21/116").
  - Local copy: `Financial Cycles – Early Warning - SSRN-id3970194.pdf`

## Methods the paper builds on (cited by us)

- **Christiano, L. J. & Fitzgerald, T. J. (2003). "The Band Pass Filter."
  International Economic Review 44(2), 435–465.**
  The band-pass filter we use. Free version: NBER Working Paper 7257 (1999).
  - https://www.nber.org/papers/w7257
  - PDF: https://www.nber.org/system/files/working_papers/w7257/w7257.pdf
  - Journal DOI: 10.1111/1468-2354.t01-1-00076 (paywalled)
- **Harding, D. & Pagan, A. (2002). "Dissecting the Cycle: A Methodological
  Investigation." Journal of Monetary Economics 49(2), 365–381.**
  Turning-point dating algorithm (our validation step).
- **Claessens, S., Kose, M. A. & Terrones, M. E. — (2011a) "Financial Cycles: What? How?
  When?" IMF WP/11/76; (2011b/2012) "How Do Business and Financial Cycles Interact?"
  Journal of International Economics 87(1), 178–190.**
  The specific BBQ implementation of Harding–Pagan that Chen & Svirydzenka follow for cycle
  dating: run on the log-level, min phase 2 quarters, min complete cycle 5 quarters, with
  the 2-quarter min-phase waived when a one-quarter asset-price decline exceeds 20%.
  - IMF WP/11/76: https://www.imf.org/external/pubs/ft/wp/2011/wp1176.pdf  (bot-403)
  - JIE 2012 (author copy, readable): https://www.marcoterrones.com/uploads/1/7/6/9/17698985/ckt_2012_how_do_business_and_financial_cycles_interact_jie.pdf
- **Kaminsky, G., Lizondo, S. & Reinhart, C. (1998). "Leading Indicators of Currency
  Crises." IMF Staff Papers 45(1).**
  Signal-extraction threshold approach behind the paper's EWS loss function (eq. 4).
- **Laeven, L. & Valencia, F. (2018). "Systemic Banking Crises Revisited."
  IMF Working Paper 18/206.**
  Crisis database the thresholds were calibrated on; basis for the "Canada has no
  systemic banking crisis" framing.

## Software implementation

- **statsmodels `cffilter` (Christiano–Fitzgerald filter), version 0.14.6.**
  Exact code we run for the band-pass filter (incl. the drift adjustment, which the IMF
  paper does not specify — it is an implementation detail from here / CF 2003).
  - Docs: https://www.statsmodels.org/stable/generated/statsmodels.tsa.filters.cf_filter.cffilter.html
  - Source (pinned): https://github.com/statsmodels/statsmodels/blob/v0.14.6/statsmodels/tsa/filters/cf_filter.py
- Python stack pinned in `requirements.txt` (numpy, pandas, scipy, statsmodels).

## Data — series used

Fetched and cached by `fetch_data.py` (see `data/raw/manifest.json` for the data vintage).

**FRED (Federal Reserve Bank of St. Louis)** — `https://fred.stlouisfed.org/series/<ID>`:

| Role | FRED ID | Underlying provider |
|------|---------|---------------------|
| Real GDP, Canada | NGDPRSAXDCCAQ | OECD / IMF |
| Share prices, Canada | SPASTT01CAQ661N | OECD Main Economic Indicators |
| Total credit to private non-fin sector | CRDQCAAPABIS | BIS |
| Total credit, % of GDP | QCAPAM770A | BIS |
| Bank credit, % of GDP | QCAPBM770A | BIS |
| Credit-to-GDP | QCACAM770A | BIS |
| Real residential property prices | QCAR628BIS | BIS |
| CPI (cross-check only) | CANCPIALLQINMEI, CANCPIALLMINMEI | OECD |

**Statistics Canada** — CPI deflator (the one we actually use):

- CPI, all-items, Canada, monthly, 2002=100 — **vector v41690973**, table **18-10-0004-01**.
  - https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401
  - Pulled via the StatCan Web Data Service (WDS) API.

**Bank of Canada** — official quarterly output gap (Phase-3 cross-check of our filtered GDP
gap; validation only), via the Valet API `https://www.bankofcanada.ca/valet/observations/<code>/json`:

| Role | BoC series (Valet code) |
|------|-------------------------|
| Output gap — Current MPR | INDINF_OUTGAPMPR_Q |
| Output gap — Integrated Framework | INDINF_OUTGAPI_Q |
| Output gap — Extended Multivariate Filter | INDINF_OUTGAPM_Q |

## Data providers (for attribution)

- Federal Reserve Bank of St. Louis (FRED) — data aggregator.
- OECD Main Economic Indicators — share prices, GDP.
- Bank for International Settlements (BIS) — credit and property prices.
- Statistics Canada — Consumer Price Index.
- Bank of Canada — official output-gap estimates (GDP-gap cross-check).
