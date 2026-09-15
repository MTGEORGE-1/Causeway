"""Sharded export.

At ~2,800 companies a single payload runs to tens of megabytes, which would make
the page slow to open and pointless to cache. So it splits:

* `site/data.js` — a light search index, everything the list view needs and
  nothing more. Loads instantly.
* `site/co/<code>.json` — the full record for one company, fetched only when
  someone opens it.

`fetch()` is blocked on `file://` URLs, so opening `site/index.html` directly
from Finder can load the index but not the per-company files. `serve.py` exists
for that; on GitHub Pages it is served over HTTP and simply works.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
CO = SITE / "co"
ARTIFACTS = ROOT / "data" / "artifacts"


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 6)
    if isinstance(o, pd.Timestamp):
        return str(o.date())
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    return o


def write(companies: list[dict], meta: dict, lineage: list) -> dict:
    CO.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for old in CO.glob("*.json"):
        old.unlink()

    index = []
    for c in companies:
        p = c.get("profile") or {}
        mk = c.get("markets") or {}
        q = c.get("quote") or {}
        index.append({
            "px": q.get("price"),
            "chg": q.get("change"),
            "chgp": q.get("change_pct"),
            "cur": q.get("currency"),
            "asof": q.get("as_of"),
            "code": c["code"],
            "ticker": c["ticker"],
            "name": c["name"],
            "hkex_name": c["hkex_name"],
            "board": c["board"],
            "sector": p.get("sector"),
            "industry": p.get("industry"),
            "mcap": p.get("market_cap_usd"),
            "r1y": (c.get("price") or {}).get("return_1y"),
            "driver": (mk.get("driver") or {}).get("market"),
            "gap": (mk.get("gap") or {}).get("value"),
            # Profile coverage is rationed by an upstream rate limit, so the
            # list view says which companies already carry one instead of
            # letting a reader discover the gap by clicking.
            "prof": 1 if p.get("name") else 0,
            "ceo": 1 if p.get("officers") else 0,
        })
        (CO / f"{c['code']}.json").write_text(
            json.dumps(_clean(c), ensure_ascii=False, separators=(",", ":")))

    index.sort(key=lambda r: r["mcap"] or 0, reverse=True)

    payload = {
        "meta": _clean(meta),
        "index": _clean(index),
        "lineage": _clean(lineage),
        "limitations": [
            "Chart annotations are detected from the price series, not written by a "
            "human. They mark what is structurally notable (the peak, the trough, the "
            "worst drawdown, the biggest sessions) and describe the move, never its "
            "cause. A -18% day is labelled a -18% day, not a profit warning.",
            "Market relationships are statistical, not causal. A high mainland beta says "
            "the shares move with Shanghai; it does not prove where revenue comes from.",
            "Weekly returns are used throughout. Hong Kong closes before New York opens, "
            "and the mainland runs a different holiday calendar, so daily co-movement "
            "would understate these relationships mechanically.",
            "Directors and executives come from Yahoo Finance and can lag real "
            "appointments. Treat the C-suite panel as a starting point, not a filing.",
            "Company profiles (business description, sector, financials and the C-suite) "
            "come from an endpoint that rate-limits by IP and cannot serve the whole board "
            "in one build. Coverage accumulates across nightly runs, largest companies "
            "first. Price history, chart annotations and the three-market comparison are "
            "unaffected and cover the whole board.",
            "Coverage thins toward the small end of the board. Many GEM names are barely "
            "traded, and some carry no fundamentals at all, so those fields show as blank "
            "rather than zero.",
            "Money is converted to USD at current spot. Financial figures come from "
            "Yahoo Finance and restatements are common.",
            "Prices are the last close from the most recent build, not a live tick. "
            "Every price carries the date it was taken. A genuinely live quote would need "
            "a paid market-data feed, because a static page cannot call the free sources "
            "directly from a browser.",
            "Nothing here is a forecast or investment advice.",
        ],
    }

    (SITE / "data.js").write_text(
        "// Generated by hkex.export. Do not edit by hand.\n"
        "window.HKEX = " + json.dumps(payload, ensure_ascii=False,
                                      separators=(",", ":")) + ";\n")
    (ARTIFACTS / "hkex_index.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False))

    size = sum(f.stat().st_size for f in CO.glob("*.json"))
    return {"index_kb": (SITE / "data.js").stat().st_size / 1024,
            "shards": len(list(CO.glob("*.json"))),
            "shard_mb": size / 1024 / 1024}
