"""Turn raw data into the per-company analysis the page shows.

The US-exposure reading has two independent halves, and keeping them separate is
the point of the whole feature:

* **Computed** — how strongly the stock actually moves with the US market, from
  a regression of weekly returns on the S&P 500. This is measured, updates every
  build, and cannot be argued with.
* **Curated** — how the company actually sells into the US: channel, regulatory
  status, tariff exposure. Hand-researched, dated, and carrying a confidence
  level.

They answer different questions and they frequently disagree. NIO is US-listed
and trades with US risk appetite while selling exactly zero cars in America; Yum
China is US-listed with no US revenue at all. A single blended score would hide
precisely the thing worth seeing, so no blended score is produced.

Weekly returns rather than daily: Hong Kong closes before New York opens, so
daily co-movement understates the true relationship for mechanical reasons.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .universe import ACCESS_META, US_EXPOSURE

TRADING_DAYS = 252


def _weekly(s: pd.Series) -> pd.Series:
    return np.log(s.resample("W-FRI").last().dropna()).diff().dropna()


def us_beta(px: pd.Series, bench: pd.Series, years: int = 5) -> dict:
    """Regress weekly stock returns on weekly S&P 500 returns."""
    cutoff = px.index.max() - pd.Timedelta(days=365 * years)
    a, b = _weekly(px[px.index >= cutoff]), _weekly(bench[bench.index >= cutoff])
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    j.columns = ["y", "x"]
    if len(j) < 52:
        return {"beta": None, "correlation": None, "r_squared": None, "n_weeks": len(j)}

    x, y = j["x"].to_numpy(), j["y"].to_numpy()
    vx = x.var()
    beta = float(np.cov(x, y)[0, 1] / vx) if vx > 0 else None
    corr = float(np.corrcoef(x, y)[0, 1])
    return {"beta": beta, "correlation": corr, "r_squared": corr ** 2,
            "n_weeks": len(j)}


def price_stats(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) < 30:
        return {}
    out = {"last": float(s.iloc[-1]),
           "listed_from": str(s.index[0].date()),
           "years": round((s.index[-1] - s.index[0]).days / 365.25, 1)}

    lr = np.log(s).diff().dropna()
    out["volatility"] = float(lr.std() * np.sqrt(TRADING_DAYS))
    out["max_drawdown"] = float((s / s.cummax() - 1).min())

    for label, days in (("1y", 365), ("3y", 365 * 3), ("5y", 365 * 5), ("10y", 365 * 10)):
        w = s[s.index >= s.index.max() - pd.Timedelta(days=days)]
        if len(w) > 20:
            yrs = (w.index[-1] - w.index[0]).days / 365.25
            out[f"return_{label}"] = float(w.iloc[-1] / w.iloc[0] - 1)
            if yrs >= 0.9 and w.iloc[0] > 0:
                out[f"cagr_{label}"] = float((w.iloc[-1] / w.iloc[0]) ** (1 / yrs) - 1)

    hi, lo = float(s[-252:].max()), float(s[-252:].min())
    out["pct_of_52w_high"] = float(s.iloc[-1] / hi) if hi else None
    out["range_52w"] = [lo, hi]
    return out


def _verdict(prof: dict, ps: dict, ub: dict, exp: dict | None) -> list[str]:
    """Three or four plain sentences a reader can act on.

    Deliberately assembled from thresholds rather than written per company, so
    the same evidence always produces the same wording.
    """
    out = []
    rg = prof.get("revenue_growth_yoy")
    pm = prof.get("profit_margin")

    if rg is not None:
        if rg > 0.25:
            out.append(f"Revenue is growing fast — up {rg*100:.0f}% year on year.")
        elif rg > 0.05:
            out.append(f"Revenue is growing steadily, up {rg*100:.0f}% year on year.")
        elif rg > -0.02:
            out.append("Revenue is broadly flat year on year.")
        else:
            out.append(f"Revenue is shrinking, down {abs(rg)*100:.0f}% year on year.")

    if pm is not None:
        if pm < 0:
            out.append(f"It is lossmaking, with a net margin of {pm*100:.1f}%.")
        elif pm < 0.05:
            out.append(f"Margins are thin at {pm*100:.1f}% — typical of hardware and "
                       "volume manufacturing.")
        elif pm > 0.2:
            out.append(f"Margins are strong at {pm*100:.0f}%.")
        else:
            out.append(f"Net margin is {pm*100:.1f}%.")

    c5 = ps.get("cagr_5y")
    if c5 is not None:
        if c5 > 0.15:
            out.append(f"Shareholders have done well — {c5*100:.0f}% a year over five years.")
        elif c5 > 0:
            out.append(f"The shares have returned {c5*100:.1f}% a year over five years.")
        else:
            out.append(f"The shares have lost {abs(c5)*100:.1f}% a year over five years.")

    b = ub.get("beta")
    if b is not None and exp:
        acc = exp.get("access")
        if acc in ("blocked", "domestic") and b > 0.8:
            out.append("Notably, it trades with the US market despite selling little or "
                       "nothing there — this is sentiment, not business exposure.")
        elif acc == "open" and b is not None:
            out.append(f"Its US linkage is real on both counts: it sells there, and its "
                       f"shares move with the S&P 500 (beta {b:.2f}).")
    return out


def build(prices: pd.DataFrame, profiles: dict, universe, benchmark: str) -> list[dict]:
    bench = prices[benchmark].dropna() if benchmark in prices.columns else pd.Series(dtype=float)
    rows = []

    for co in universe:
        prof = profiles.get(co.ticker, {})
        s = prices[co.ticker].dropna() if co.ticker in prices.columns else pd.Series(dtype=float)
        if s.empty and not prof:
            continue

        ps = price_stats(s)
        ub = us_beta(s, bench) if (not s.empty and not bench.empty) else {}
        exp = US_EXPOSURE.get(co.ticker)

        rows.append({
            "ticker": co.ticker,
            "name": prof.get("name") or co.name,
            "short_name": co.name,
            "sector": co.sector,
            "adr": co.adr,
            "tags": list(co.tags),
            "profile": {k: prof.get(k) for k in (
                "summary", "industry", "country", "website", "employees",
                "market_cap_usd", "revenue_usd", "revenue_growth_yoy",
                "earnings_growth_yoy", "profit_margin", "gross_margin",
                "operating_margin", "roe", "pe", "forward_pe", "price_to_book",
                "debt_to_equity", "free_cashflow_usd", "dividend_yield",
                "capex_usd", "capex_intensity", "revenue_cagr",
                "revenue_cagr_years", "revenue_history", "currency_market")},
            "price": ps,
            "us_market_link": ub,
            "us_business": ({**exp, "meta": ACCESS_META.get(exp["access"], {})}
                            if exp else None),
            "verdict": _verdict(prof, ps, ub, exp),
        })

    rows.sort(key=lambda r: r["profile"].get("market_cap_usd") or 0, reverse=True)
    return rows
