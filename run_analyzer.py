#!/usr/bin/env python3
"""China Company Analyzer — build.

    python run.py            # use cache where fresh
    python run.py --force    # re-fetch everything (~60 API calls, ~90s)

Writes data/artifacts/analyzer.json and site/data.js, then open site/index.html.

Earlier builds are still here: run_versus.py (China vs US sector comparison)
and run_regime.py (regime classifier).
"""

from __future__ import annotations

import argparse
import sys
import time

from analyzer import analyze, export, ingest
from analyzer.universe import BENCHMARK, UNIVERSE, US_EXPOSURE, tickers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    print("China Company Analyzer — build\n" + "=" * 60)

    ts = tickers()
    print(f"[1/4] ingest — {len(ts)} companies")
    fx = ingest.fetch_fx(force=args.force)
    print(f"      FX     CNY={fx.get('CNY', 0):.4f}  HKD={fx.get('HKD', 0):.4f}")

    prices = ingest.fetch_prices(ts, BENCHMARK, force=args.force)
    print(f"      prices {prices.shape[1]} series, {len(prices)} days")

    print("      profiles — one call per company, please wait…")
    profiles = ingest.fetch_profiles(ts, fx, force=args.force)
    print(f"      profiles {len(profiles)}/{len(ts)}")

    print("[2/4] analyze")
    companies = analyze.build(prices, profiles, UNIVERSE, BENCHMARK)
    covered = sum(1 for c in companies if c["us_business"])
    with_beta = sum(1 for c in companies if c["us_market_link"].get("beta") is not None)
    print(f"      {len(companies)} analysed")
    print(f"      US business profile: {covered}/{len(companies)} curated")
    print(f"      US-market beta:      {with_beta}/{len(companies)} computed")

    print("[3/4] export")
    payload = export.build_payload(companies, prices, ingest.LINEAGE)
    export.write(payload)

    print("[4/4] done")
    print("=" * 60)

    buckets: dict[str, int] = {}
    for c in companies:
        if c["us_business"]:
            k = c["us_business"]["access"]
            buckets[k] = buckets.get(k, 0) + 1
    print("US access breakdown:")
    for k in ("open", "tariffed", "restricted", "blocked", "domestic"):
        if k in buckets:
            print(f"  {k:<11} {buckets[k]:>3}")

    missing = [c.ticker for c in UNIVERSE if c.ticker not in US_EXPOSURE]
    if missing:
        print(f"\nNo curated US profile yet: {', '.join(missing)}")

    print(f"\nBuilt in {time.time() - t0:.1f}s. Open site/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
