# China Company Analyzer

Type a ticker — `BYD`, `0981.HK`, `Tencent` — and get an analysis of what that company does,
how it is performing, and **how exposed it is to the United States**.

61 major Chinese listed companies across six sectors.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py          # --force to re-fetch (~70s)
open site/index.html
```

Live: **https://mtgeorge-1.github.io/transmission/** — rebuilt automatically each weekday.

---

## The US exposure panel

This is the part that does not exist elsewhere. It answers **two different questions side by
side**, and refuses to blend them into a single score — because the interesting cases are
exactly the ones where they disagree.

| | **How it sells in the US** | **How it trades with the US** |
|---|---|---|
| Source | Hand-researched, dated, confidence-rated | Computed from market data every build |
| Shows | Sales channel, regulatory status, tariffs, disclosed US revenue share | Beta and correlation to the S&P 500 |

Companies are rated on US market access:

**Sells openly** · **Sells, exposed to tariffs** · **Restricted by US policy** ·
**Effectively blocked** · **Little or no US business**

Worked examples:

- **BYD** — *effectively blocked* (buses only, 100% tariff on Chinese EVs), yet beta 0.44. It
  trades partly on US sentiment while selling no cars there.
- **NIO** — US-listed, US R&D office, **zero** US revenue. A listing is not a market.
- **Yum China** — US-listed, operates KFC inside China, zero US revenue. The mirror image.
- **Techtronic** — Hong Kong-listed, but owns Milwaukee Tool and Ryobi and sells through Home
  Depot. Beta 1.00. Real US linkage on both counts.
- **SMIC** — restricted, but the binding constraint is what it can *buy* (lithography under
  export controls), not what it can sell.
- **PDD/Temu** — the most tariff-sensitive name here; its US model was built on the $800 de
  minimis exemption that no longer exists.

Current split: 15 open · 4 tariffed · 6 restricted · 8 blocked · 28 domestic.

## What each company page shows

- What it does — business description, sector, industry, headcount
- A plain-language verdict generated from thresholds, so identical evidence always reads the same
- Market cap, revenue, growth, margins, P/E, price/book, capex intensity
- Ten-year share price chart
- Returns over 1 / 3 / 5 / 10 years, total and annualised
- Risk and quality — volatility, max drawdown, % of 52-week high, ROE, free cash flow

## Honest limits

- **The US business data is hand-curated as of 2026-05** and does not update nightly. Financials
  and prices do. The page keeps the two visually separate and stamps the curated date, because a
  stale regulatory status is worse than none if you cannot tell which is which.
- **US revenue share is blank unless disclosed.** Blank means not disclosed, not zero.
- **Beta is sentiment linkage, not revenue.** Weekly returns are used because Hong Kong closes
  before New York opens; daily co-movement would understate the relationship mechanically.
- **A-share-only companies are missing** — geo-blocked from this network. That costs Cambricon,
  Hygon, NAURA, AMEC and iFlytek. See [PHASE0_FINDINGS.md](PHASE0_FINDINGS.md).
- All money is converted to USD at spot. yfinance reports market cap in listing currency and
  financials in `financialCurrency` and the two disagree constantly — SMIC lists in Hong Kong but
  reports USD, BYD reports CNY. Unconverted that is a 7× error.
- Nothing here is a forecast or investment advice.

## Layout

```
analyzer/
  universe.py   61 companies + curated US_EXPOSURE table
  ingest.py     prices, profiles, financials, S&P 500; USD-normalised, cached
  analyze.py    metrics, US-market beta, plain-language verdict
  export.py     JSON artifact + site/data.js
run.py          orchestrator
site/index.html the lookup page
```

Deploy: [DEPLOY.md](DEPLOY.md). Every push to `main` rebuilds and redeploys.

## Earlier builds, still working

- `run_versus.py` + `versus/` — China vs US sector comparison across 90 companies
- `run_regime.py` + `transmission/` — 4-state hidden Markov regime classifier. It identified the
  June 2015 bubble-to-crash handoff without being given the dates. Original plan in
  [SCOPING.md](SCOPING.md).
