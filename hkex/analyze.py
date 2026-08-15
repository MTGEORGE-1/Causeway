"""Assemble the per-company record."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import events, markets

TRADING_DAYS = 252


def price_stats(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) < 30:
        return {}
    out = {
        "last": float(s.iloc[-1]),
        "first_date": str(s.index[0].date()),
        "last_date": str(s.index[-1].date()),
        "years": round((s.index[-1] - s.index[0]).days / 365.25, 1),
    }
    lr = np.log(s).diff().dropna()
    out["volatility"] = float(lr.std() * np.sqrt(TRADING_DAYS))
    out["max_drawdown"] = float((s / s.cummax() - 1).min())

    for lbl, years in (("1y", 1), ("3y", 3), ("5y", 5)):
        w = s[s.index >= s.index.max() - pd.Timedelta(days=365 * years)]
        if len(w) <= 20 or w.iloc[0] <= 0:
            continue
        yrs = (w.index[-1] - w.index[0]).days / 365.25
        # A window is only published under its label if the history actually
        # covers it. CATL listed in May 2025, and its 1.2 years of history was
        # shipping unchanged as both return_3y and return_5y — the same number
        # under two labels, neither of them true.
        if yrs < years * 0.85:
            continue
        out[f"return_{lbl}"] = float(w.iloc[-1] / w.iloc[0] - 1)
        out[f"cagr_{lbl}"] = float((w.iloc[-1] / w.iloc[0]) ** (1 / yrs) - 1)
        out[f"span_{lbl}"] = round(yrs, 2)

    w52 = s[s.index >= s.index.max() - pd.Timedelta(days=365)]
    if len(w52):
        hi, lo = float(w52.max()), float(w52.min())
        out["high_52w"], out["low_52w"] = hi, lo
        out["pct_of_52w_high"] = float(s.iloc[-1] / hi) if hi else None
    return out


def _summary_lines(prof: dict, ps: dict, mk: dict) -> list[str]:
    """Plain-language read, assembled from thresholds so identical evidence
    always produces identical wording."""
    out = []
    r1 = ps.get("return_1y")
    if r1 is not None:
        if r1 > 0.3:
            out.append(f"Up {r1*100:.0f}% over the past year.")
        elif r1 > 0.05:
            out.append(f"Up {r1*100:.0f}% over the past year.")
        elif r1 > -0.05:
            out.append("Broadly flat over the past year.")
        else:
            out.append(f"Down {abs(r1)*100:.0f}% over the past year.")

    pk = ps.get("pct_of_52w_high")
    if pk is not None:
        if pk > 0.95:
            out.append("Trading near its 52-week high.")
        elif pk < 0.6:
            out.append(f"Trading {(1-pk)*100:.0f}% below its 52-week high.")

    rg, pm = prof.get("revenue_growth"), prof.get("profit_margin")
    if rg is not None and pm is not None:
        if pm < 0:
            out.append(f"Lossmaking, with revenue {'growing' if rg>0 else 'shrinking'} "
                       f"{abs(rg)*100:.0f}%.")
        elif rg > 0.15:
            out.append(f"Revenue growing {rg*100:.0f}% with a {pm*100:.0f}% net margin.")
        elif rg < -0.05:
            out.append(f"Revenue shrinking {abs(rg)*100:.0f}%, net margin {pm*100:.0f}%.")

    d = mk.get("driver") or {}
    if d.get("text"):
        out.append(d["text"])
    return out


def quote(s: pd.Series, currency: str = "HKD") -> dict:
    """Latest close and the move on that session.

    This is the number a reader recognises from a search engine — price, and
    what it did today. It is as fresh as the last build, which the page states
    rather than implying a live tick.
    """
    s = s.dropna()
    if len(s) < 2:
        return {}
    last, prev = float(s.iloc[-1]), float(s.iloc[-2])
    return {
        "price": last,
        "prev_close": prev,
        "change": last - prev,
        "change_pct": (last / prev - 1) if prev else None,
        "as_of": str(s.index[-1].date()),
        "currency": currency,
    }


def build_one(sec, px: pd.Series, prof: dict, benchmarks: pd.DataFrame) -> dict:
    ps = price_stats(px)
    mk = markets.analyse(px, benchmarks) if len(px.dropna()) >= 60 else {}
    ev = events.detect(px, benchmarks)
    q = quote(px, ((prof or {}).get("currency") or "HKD"))

    weekly = px.dropna().resample("W-FRI").last().dropna()
    series = [{"d": str(pd.Timestamp(i).date()), "v": round(float(v), 3)}
              for i, v in weekly.items()]

    return {
        "code": sec.code,
        "ticker": sec.ticker,
        "hkex_name": sec.name,
        "board": sec.board,
        "name": (prof or {}).get("name") or sec.name,
        "profile": prof or {},
        "quote": q,
        "price": ps,
        "markets": mk,
        "events": ev,
        "series": series,
        "read": _summary_lines(prof or {}, ps, mk),
    }
