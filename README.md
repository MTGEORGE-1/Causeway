# HKEX Explorer

Look up any company on the Hong Kong Stock Exchange and get three things:

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

## Chart annotations are detected, not written

Hand-authoring notes for 2,716 companies is not possible, and doing it for the famous twenty
would leave everything else blank. So the chart marks what is structurally notable in the
series — five-year high and low, deepest drawdown, biggest one-day moves, strongest
three-month run — and describes each one.

**They describe the move, never its cause.** A −13% day is labelled a −13% day, not a profit
warning. Inferring reasons from price alone is how you end up confidently wrong.

## Known limits — read this one

**Company profiles cover 665 of 2,716 companies, and that number grows every build.**

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
