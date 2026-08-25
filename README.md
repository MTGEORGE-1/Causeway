# Causeway 銅鑼灣

A deep dive into the Hong Kong Stock Exchange. Look up any listed company and get three things:

1. **A five-year price chart with the notable points marked** — peak, trough, worst drawdown,
   biggest single sessions, strongest run.
2. **Which market actually moves it** — the US, Hong Kong, or mainland China — and specifically
   the difference between mainland and Hong Kong.
3. **Who runs it** — CEO, CFO and the rest of the named leadership.

Built from HKEX's own *List of Securities*: **2,716 companies** across the Main Board, GEM,
REITs and investment companies.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
.venv/bin/python serve.py     # opens the site
```

`serve.py` is needed locally because the page loads one file per company and browsers block
that on `file://` URLs. On GitHub Pages it is served over HTTP and just works.

---

## Which market moves this stock

The reason the tool exists. Every company here trades in Hong Kong, which tells you almost
nothing about what actually drives it. Three regressions of weekly returns answer it:

| | Benchmark | What it captures |
|---|---|---|
| **United States** | S&P 500 | Global risk appetite, the dollar cycle |
| **Hong Kong** | Hang Seng | Local liquidity, the flows that clear the trade |
| **Mainland China** | CSI 300 | Beijing's policy cycle, domestic sentiment |

Across the board: **942 move with Hong Kong, 178 with the mainland, 15 with the US**, and
1,581 have no clear driver at all — mostly small and thinly traded, which is itself the finding.

Tencent is the clean illustration: beta 1.34 to Hong Kong and 1.19 to the mainland, but Hong
Kong explains 69% of its weekly moves against the mainland's 28%. It is a Chinese company whose
share price is set by Hong Kong and global money.

Weekly rather than daily returns throughout: Hong Kong closes before New York opens and the
mainland runs a different holiday calendar, so daily co-movement understates these
relationships for purely mechanical reasons.

## Try a scenario

Inside the market panel, set where you think the S&P 500, Hang Seng and CSI 300 land five
years out. Causeway works through what that implies for the share price, year by year, with a
range around it.

The arithmetic runs in log space, because that is how the betas were fitted: an index moving
L0 to L1 is a log return of `ln(L1/L0)`, the stock's implied log return is the sum of each
sensitivity times its index's log return, and `exp()` converts back to a price.

**The sensitivities are not the three betas shown above them.** Those are measured one index
at a time, and the three indices largely move together — adding them up would count the same
worldwide risk-on week three times over. The scenario uses a joint fit, where each coefficient
is the effect of that index holding the other two still. For Tencent the single betas are 0.30
/ 1.33 / 1.19; jointly they are −0.18 / 1.40 / −0.07, which says the mainland relationship was
Hong Kong's all along.

Two deliberate choices:

- **Alpha is excluded.** Carrying five years of past company-specific drift into a forward
  projection would bake in a prediction the user never made.
- **The range is the residual.** Whatever the indices do not explain, scaled by the square root
  of the horizon — roughly two outcomes in three.

Where the indices explain under 20% of a stock's movement, the panel says so before showing
any number. That is **2,165 of 2,629 companies** — most of the board is not market-driven, and
the tool should say so rather than let someone read meaning into a number that has none.

It is arithmetic on a historical relationship, not a forecast.

## Chart annotations are detected, not written

Hand-authoring notes for 2,716 companies is not possible, and doing it for the famous twenty
would leave everything else blank. So the chart marks what is structurally notable in the
series — five-year high and low, deepest drawdown, biggest one-day moves, strongest
three-month run — and describes each one.

**They describe the move, never its cause.** A −13% day is labelled a −13% day, not a profit
warning. Inferring reasons from price alone is how you end up confidently wrong.

## Known limits — read this one

**Company profiles cover 1,104 of 2,716 companies, and that number grows every build.**

Business descriptions, sector, financials and the C-suite come from Yahoo's quote endpoint,
which rate-limits by IP and will not serve 2,782 companies in a single run — asking for all of
them returned 401s for three quarters of the board, and retrying inside the same run recovered
nothing. So each build takes a slice of about 450, largest and best-known companies first, and
the cache accumulates across runs. The nightly job restores that cache, so coverage fills in
over roughly a week and then keeps refreshing.

**Price history, chart annotations and the three-market comparison are unaffected** — they use
a different endpoint that covers the whole board in one pass. 2,716 companies have charts;
2,624 have the full three-market analysis. The list view shows how many carry a full profile,
and has a filter for them.

Other limits:

- Market relationships are statistical, not causal. A high mainland beta says the shares move
  with Shanghai; it does not prove where the revenue comes from.
- Leadership data can lag real appointments. Treat it as a starting point, not a filing.
- Coverage thins toward the small end. Many GEM names barely trade; 66 were dropped for having
  under 60 days of history.
- Money is converted to USD at spot.
- Nothing here is a forecast or investment advice.

## Layout

```
hkex/
  securities.py  parse ListOfSecurities.xlsx -> 2,782 equities
  ingest.py      batched prices, 3 benchmarks, budgeted profile fetch
  events.py      notable-point detection
  markets.py     three-market regressions + the mainland-vs-HK gap
  analyze.py     assemble the per-company record
  export.py      search index + one JSON per company
run.py           orchestrator
serve.py         local preview server
site/            the page
```

Deploy: [DEPLOY.md](DEPLOY.md). Every push to `main` rebuilds and redeploys.

## Earlier builds, still working

- `run_analyzer.py` + `analyzer/` — 61 Chinese companies with hand-researched US-exposure
- `run_versus.py` + `versus/` — China vs US sector comparison across 90 companies
- `run_regime.py` + `transmission/` — hidden Markov regime classifier; it found the June 2015
  bubble-to-crash handoff without being given the dates. Plan in [SCOPING.md](SCOPING.md).
