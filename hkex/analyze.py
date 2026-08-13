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

    for lbl, days in (("1y", 365), ("3y", 365 * 3), ("5y", 365 * 5)):
        w = s[s.index >= s.index.max() - pd.Timedelta(days=days)]
        if len(w) > 20 and w.iloc[0] > 0:
            yrs = (w.index[-1] - w.index[0]).days / 365.25
            out[f"return_{lbl}"] = float(w.iloc[-1] / w.iloc[0] - 1)
            if yrs >= 0.9:
                out[f"cagr_{lbl}"] = float((w.iloc[-1] / w.iloc[0]) ** (1 / yrs) - 1)

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


def build_one(sec, px: pd.Series, prof: dict, benchmarks: pd.DataFrame) -> dict:
    ps = price_stats(px)
    mk = markets.analyse(px, benchmarks) if len(px.dropna()) >= 60 else {}
    ev = events.detect(px)

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
        "price": ps,
        "markets": mk,
        "events": ev,
        "series": series,
        "read": _summary_lines(prof or {}, ps, mk),
    }
