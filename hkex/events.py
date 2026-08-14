"""Find the notable points on a five-year price series, and say what they were.

These annotations are **detected, not authored**. Hand-writing notes for 2,716
companies is not possible, and writing them for the famous twenty would leave
everything else blank.

The harder question is *why* a move happened. Price alone cannot answer it, and
generating a plausible-sounding reason ("profit warning", "earnings beat") from
a number is how a tool like this destroys its own credibility — it would be
right often enough to be trusted and wrong often enough to matter.

So each event is explained with what the data can actually support: whether the
move was **company-specific or market-wide**, established by comparing the same
session against the Hang Seng. "Fell 12% while the Hang Seng was flat" is a real
finding and points a reader at the right question. "Fell 12% on disappointing
results" would be a guess.
"""

from __future__ import annotations

import pandas as pd

MIN_MOVE = 0.08
MIN_DRAWDOWN = 0.20
MIN_SEPARATION_DAYS = 45

# A session where the index itself moves more than this is a market day, not a
# company day.
MARKET_DAY = 0.015


def _fmt(ts) -> str:
    return str(pd.Timestamp(ts).date())


def _market_context(date, stock_move: float, bench: pd.DataFrame | None) -> str:
    """Was this the company, or the whole market?"""
    if bench is None or "hk" not in bench.columns or stock_move is None:
        return ""
    hk = bench["hk"].dropna()
    ret = hk.pct_change()
    ts = pd.Timestamp(date)
    if ts not in ret.index:
        near = ret.index[ret.index.get_indexer([ts], method="nearest")]
        if not len(near) or abs((near[0] - ts).days) > 3:
            return ""
        ts = near[0]
    hk_move = float(ret.loc[ts])
    if pd.isna(hk_move):
        return ""

    same_way = (hk_move > 0) == (stock_move > 0)
    if abs(hk_move) >= MARKET_DAY and same_way:
        return (f"The whole market moved that day — the Hang Seng was "
                f"{hk_move*100:+.1f}%, so this was not company-specific.")
    if abs(hk_move) < 0.005:
        return (f"The Hang Seng was flat that day ({hk_move*100:+.1f}%), so this "
                "was specific to the company.")
    return (f"The Hang Seng was {hk_move*100:+.1f}% that day, so most of this "
            "was specific to the company.")


def detect(s: pd.Series, bench: pd.DataFrame | None = None,
           max_events: int = 6) -> list[dict]:
    s = s.dropna()
    if len(s) < 60:
        return []

    events: list[dict] = []
    ret = s.pct_change()

    hi_d, lo_d = s.idxmax(), s.idxmin()
    events.append({
        "date": _fmt(hi_d), "price": float(s.loc[hi_d]), "kind": "high",
        "priority": 1, "title": "Five-year high",
        "detail": f"The highest close of the period, at {s.loc[hi_d]:,.2f}.",
        "context": ""})
    events.append({
        "date": _fmt(lo_d), "price": float(s.loc[lo_d]), "kind": "low",
        "priority": 1, "title": "Five-year low",
        "detail": f"The lowest close of the period, at {s.loc[lo_d]:,.2f}.",
        "context": ""})

    roll_max = s.cummax()
    dd = s / roll_max - 1
    trough = dd.idxmin()
    depth = float(dd.loc[trough])
    if depth <= -MIN_DRAWDOWN:
        peak_before = s.loc[:trough].idxmax()
        months = max(1, round((pd.Timestamp(trough) - pd.Timestamp(peak_before)).days / 30))
        events.append({
            "date": _fmt(trough), "price": float(s.loc[trough]), "kind": "drawdown",
            "priority": 2, "title": f"Worst drawdown, {depth*100:.0f}%",
            "detail": f"The end of the deepest fall of the period — down "
                      f"{abs(depth)*100:.0f}% over about {months} months from its "
                      f"{_fmt(peak_before)} peak.",
            "context": ""})

    for kind, idx in (("spike", ret.idxmax()), ("drop", ret.idxmin())):
        if pd.isna(idx):
            continue
        move = float(ret.loc[idx])
        if abs(move) < MIN_MOVE:
            continue
        events.append({
            "date": _fmt(idx), "price": float(s.loc[idx]), "kind": kind,
            "priority": 3,
            "title": f"Biggest one-day {'gain' if move > 0 else 'fall'}, {move*100:+.1f}%",
            "detail": f"The largest single session of the period.",
            "context": _market_context(idx, move, bench)})

    if len(s) > 140:
        roll = s.pct_change(60)
        best = roll.idxmax()
        if pd.notna(best) and float(roll.loc[best]) > 0.5:
            start = s.index[max(0, s.index.get_loc(best) - 60)]
            events.append({
                "date": _fmt(best), "price": float(s.loc[best]), "kind": "rally",
                "priority": 4,
                "title": f"Strongest run, +{roll.loc[best]*100:.0f}%",
                "detail": f"The end of its best three-month stretch, rising "
                          f"{roll.loc[best]*100:.0f}% from {_fmt(start)}.",
                "context": ""})

    events.sort(key=lambda e: (e["priority"], e["date"]))
    kept: list[dict] = []
    for e in events:
        d = pd.Timestamp(e["date"])
        if all(abs((d - pd.Timestamp(k["date"])).days) >= MIN_SEPARATION_DAYS
               for k in kept):
            kept.append(e)
        if len(kept) >= max_events:
            break

    kept.sort(key=lambda e: e["date"])
    return kept
