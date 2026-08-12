#!/usr/bin/env python3
"""China vs US — build the comparison engine.

    python run.py            # use cache where fresh
    python run.py --force    # re-fetch everything (slow: ~100 API calls)

Writes data/artifacts/versus.json and site/data.js, then open site/index.html.

The regime engine is still here and still runs — see run_regime.py.
"""

from __future__ import annotations

import argparse
import sys
import time

from versus import export, ingest, metrics
from versus.sectors import SECTORS, all_tickers


def _fmt_b(v):
    """USD into a readable scale."""
    if not v:
        return "—"
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(v) >= div:
            return f"${v / div:,.1f}{suf}"
    return f"${v:,.0f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignore cache, re-fetch")
    args = ap.parse_args()

    t0 = time.time()
    print("China vs US — build\n" + "=" * 64)

    tickers = all_tickers()
    print(f"[1/4] ingest — {len(tickers)} tickers across {len(SECTORS)} sectors")

    fx = ingest.fetch_fx(force=args.force)
    print(f"      FX     CNY={fx.get('CNY', 0):.4f}  HKD={fx.get('HKD', 0):.4f}  "
          f"EUR={fx.get('EUR', 0):.4f}")

    prices = ingest.fetch_prices(tickers, force=args.force)
    print(f"      prices {prices.shape[1]} resolved, {len(prices)} days "
          f"from {prices.index[0].date()}")

    print("      fundamentals — one call per ticker, please wait…")
    fund = ingest.fetch_fundamentals(tickers, fx, force=args.force)
    print(f"      fundamentals {len(fund)}/{len(tickers)}")

    print("[2/4] metrics")
    sectors = metrics.build(prices, fund)
    for key, s in sectors.items():
        cn, us = s["cn"], s["us"]
        cn_c = cn["index_cagr"]
        us_c = us["index_cagr"]
        print(f"      {s['label']:<32} "
              f"CN {(cn_c * 100 if cn_c else 0):>6.1f}%/yr   "
              f"US {(us_c * 100 if us_c else 0):>6.1f}%/yr")

    print("[3/4] export")
    payload = export.build_payload(sectors, fx, ingest.LINEAGE)
    export.write(payload)

    print("[4/4] done")
    print("=" * 64)
    for key, s in sectors.items():
        cn_m = s["cn"]["aggregate"]["market_cap_usd"]
        us_m = s["us"]["aggregate"]["market_cap_usd"]
        print(f"{s['label']:<32} mcap  CN {_fmt_b(cn_m):>9}   US {_fmt_b(us_m):>9}")

    print(f"\nBuilt in {time.time() - t0:.1f}s. Open site/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
