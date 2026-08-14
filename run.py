#!/usr/bin/env python3
"""Crosscurrent — build.

    python run.py            # use cache where fresh
    python run.py --force    # re-fetch everything (~8 min for the full board)
    python run.py --limit 200    # quick pass over the largest names only

Then, because the page fetches per-company files and browsers block that on
file:// URLs:

    python serve.py
"""

from __future__ import annotations

import argparse
import sys
import time

from hkex import analyze, export, ingest, securities


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="only process the first N codes (development)")
    ap.add_argument("--quotes", action="store_true",
                    help="intraday refresh: re-fetch prices, leave profiles alone. "
                         "Profiles come from a rate-limited endpoint, so a run every "
                         "30 minutes must not touch it or it burns the daily budget "
                         "and the nightly slice gets nothing.")
    args = ap.parse_args()

    t0 = time.time()
    print("Crosscurrent — build\n" + "=" * 62)

    secs = securities.load()
    stamp = securities.as_of()
    if args.limit:
        secs = secs[:args.limit]
    print(f"[1/5] universe — {len(secs)} equities from ListOfSecurities.xlsx "
          f"(HKEX as at {stamp})")

    print("[2/5] ingest")
    fx = ingest.fetch_fx(force=args.force)
    bench = ingest.fetch_benchmarks(force=args.force)
    print(f"      benchmarks {list(bench.columns)} — {len(bench)} days")

    # Profile coverage is rationed by Yahoo's rate limit and fills in over
    # several runs, so the order matters: the names someone is actually likely
    # to search must be fetched first. Heavyweights explicitly, then the Main
    # Board by stock code (Hong Kong's oldest and largest issuers hold the
    # lowest codes), then GEM last.
    SEED = ["0700.HK", "9988.HK", "0005.HK", "1299.HK", "0939.HK", "1398.HK",
            "0941.HK", "3690.HK", "1211.HK", "0388.HK", "2318.HK", "0883.HK",
            "0857.HK", "0386.HK", "1810.HK", "9618.HK", "9888.HK", "0981.HK",
            "2020.HK", "0175.HK", "1024.HK", "0016.HK", "0011.HK", "0002.HK",
            "0001.HK", "0003.HK", "0006.HK", "0012.HK", "0027.HK", "0066.HK",
            "0288.HK", "0669.HK", "0762.HK", "0992.HK", "1093.HK", "1109.HK",
            "1113.HK", "1177.HK", "1288.HK", "1928.HK", "2007.HK", "2313.HK",
            "2331.HK", "2382.HK", "2388.HK", "2628.HK", "3328.HK", "3968.HK",
            "6862.HK", "9633.HK", "9999.HK", "1347.HK", "2015.HK", "9868.HK",
            "9866.HK", "3750.HK", "9660.HK", "1919.HK", "0763.HK", "6060.HK"]
    seed_rank = {t: i for i, t in enumerate(SEED)}
    by_ticker = {s.ticker: s for s in secs}

    def priority(t: str):
        s = by_ticker[t]
        return (seed_rank.get(t, 10_000),
                0 if s.board == "Main Board" else 1,
                s.code)

    tickers = sorted((s.ticker for s in secs), key=priority)
    prices = ingest.fetch_prices(tickers, force=args.force or args.quotes)
    print(f"      prices     {prices.shape[1]}/{len(tickers)} tickers, {len(prices)} days")

    profiles = ingest.fetch_profiles(tickers, fx, force=args.force,
                                     budget=0 if args.quotes else None)
    print(f"      profiles   {len(profiles)}/{len(tickers)}"
          f"{'  (unchanged — quotes-only run)' if args.quotes else ''}")

    print("[3/5] analyze")
    import pandas as pd
    companies, skipped = [], 0
    for s in secs:
        if s.ticker not in prices.columns:
            skipped += 1
            continue
        px = prices[s.ticker]
        if px.notna().sum() < 60:
            skipped += 1
            continue
        companies.append(analyze.build_one(s, px, profiles.get(s.ticker), bench))
    print(f"      {len(companies)} analysed, {skipped} skipped for thin history")

    with_officers = sum(1 for c in companies
                        if (c["profile"] or {}).get("officers"))
    with_gap = sum(1 for c in companies
                   if (c["markets"].get("gap") or {}).get("value") is not None)
    print(f"      C-suite listed:      {with_officers}/{len(companies)}")
    print(f"      three-market compare:{with_gap}/{len(companies)}")
    print(f"      annotations:         {sum(len(c['events']) for c in companies)} total")

    print("[4/5] export")
    meta = {
        "title": "Crosscurrent",
        "subtitle": "Every company listed on the Hong Kong Stock Exchange — what it "
                    "does, who runs it, and which market actually moves it.",
        "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "hkex_as_of": stamp,
        "n_companies": len(companies),
        "benchmarks": {k: v["label"] for k, v in ingest.BENCHMARKS.items()
                       if k in bench.columns},
        "fx": fx,
    }
    stats = export.write(companies, meta, ingest.LINEAGE)
    print(f"      index    {stats['index_kb']:.0f} KB")
    print(f"      shards   {stats['shards']} files, {stats['shard_mb']:.1f} MB")

    print("[5/5] done")
    print("=" * 62)
    drivers = {}
    for c in companies:
        d = (c["markets"].get("driver") or {}).get("market")
        drivers[d or "none"] = drivers.get(d or "none", 0) + 1
    print("What moves these companies:")
    for k, lbl in (("cn", "mainland China"), ("hk", "Hong Kong"),
                   ("us", "United States"), ("none", "no clear market")):
        if k in drivers:
            print(f"  {lbl:<18} {drivers[k]:>5}")

    print(f"\nBuilt in {time.time() - t0:.1f}s.  Run:  python serve.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
