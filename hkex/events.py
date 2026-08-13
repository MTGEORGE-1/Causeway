"""Find the notable points on a five-year price series.

These annotations are **detected, not written**. Hand-authoring notes for 2,800
companies is not possible, and hand-authoring them for the twenty famous ones
would leave everything else blank. So the chart marks what is structurally
notable in the series itself — the peak, the trough, the worst drawdown, the
biggest single sessions — and says plainly what each one is.

What this cannot do is tell you *why* a move happened. A -18% day is marked as a
-18% day, not as "profit warning". Inferring causes from price alone is how you
end up confidently wrong, so the labels stay descriptive.
"""

from __future__ import annotations

import pandas as pd

MIN_MOVE = 0.08          # a single session under 8% is not worth a label
MIN_DRAWDOWN = 0.20      # nor a drawdown under 20%
MIN_SEPARATION_DAYS = 45  # keep labels from stacking on top of each other


def _fmt(ts) -> str:
    return str(pd.Timestamp(ts).date())


def detect(s: pd.Series, max_events: int = 6) -> list[dict]:
    s = s.dropna()
    if len(s) < 60:
        return []

    events: list[dict] = []
    ret = s.pct_change()

    # Peak and trough of the window.
    hi_d, lo_d = s.idxmax(), s.idxmin()
    events.append({"date": _fmt(hi_d), "price": float(s.loc[hi_d]),
                   "kind": "high", "priority": 1,
                   "label": "5-year high",
                   "detail": f"Peaked at {s.loc[hi_d]:,.2f}"})
    events.append({"date": _fmt(lo_d), "price": float(s.loc[lo_d]),
                   "kind": "low", "priority": 1,
                   "label": "5-year low",
                   "detail": f"Bottomed at {s.loc[lo_d]:,.2f}"})

    # Deepest peak-to-trough fall, and where it ended.
    roll_max = s.cummax()
    dd = s / roll_max - 1
    trough = dd.idxmin()
    depth = float(dd.loc[trough])
    if depth <= -MIN_DRAWDOWN:
        peak_before = s.loc[:trough].idxmax()
        events.append({
            "date": _fmt(trough), "price": float(s.loc[trough]),
            "kind": "drawdown", "priority": 2,
            "label": f"{depth*100:.0f}% drawdown",
            "detail": f"Fell {abs(depth)*100:.0f}% from its {_fmt(peak_before)} peak"})

    # Biggest single sessions.
    for label, idx, sign in (("biggest one-day gain", ret.idxmax(), 1),
                             ("biggest one-day fall", ret.idxmin(), -1)):
        if pd.isna(idx):
            continue
        move = float(ret.loc[idx])
        if abs(move) >= MIN_MOVE:
            events.append({
                "date": _fmt(idx), "price": float(s.loc[idx]),
                "kind": "spike" if sign > 0 else "drop", "priority": 3,
                "label": f"{move*100:+.0f}% in a day",
                "detail": label.capitalize() + f" of the period ({move*100:+.1f}%)"})

    # Strongest sustained run, as a 60-session window.
    if len(s) > 140:
        roll = s.pct_change(60)
        best = roll.idxmax()
        if pd.notna(best) and float(roll.loc[best]) > 0.5:
            events.append({
                "date": _fmt(best), "price": float(s.loc[best]),
                "kind": "rally", "priority": 4,
                "label": f"+{roll.loc[best]*100:.0f}% run",
                "detail": f"Strongest three-month run of the period, "
                          f"up {roll.loc[best]*100:.0f}%"})

    # Rank, then thin out anything that would overlap on the axis.
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
