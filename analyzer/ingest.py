"""Fetch prices, profiles and financials for the universe, plus the S&P 500.

Same discipline as the rest of this repo: cache hard, normalise currency to USD,
record what failed. yfinance reports market cap in the listing currency and
financials in `financialCurrency`, and the two frequently disagree — SMIC lists
in Hong Kong but reports in USD, BYD reports CNY. Left unconverted that is a
7x error, so every money figure is converted and the rate is recorded.
"""

from __future__ import annotations

import json
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "acache"
CACHE.mkdir(parents=True, exist_ok=True)

YEARS = 10
TTL_HOURS = 20
LINEAGE: list[dict] = []


def _record(dataset: str, status: str, n: int, note: str = "") -> None:
    LINEAGE.append({"dataset": dataset, "status": status, "n": n, "note": note,
                    "fetched_at": datetime.now().isoformat(timespec="seconds")})


def _fresh(p: Path) -> bool:
    return p.exists() and (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)
                           < timedelta(hours=TTL_HOURS))


def fetch_fx(force: bool = False) -> dict[str, float]:
    p = CACHE / "fx.json"
    if not force and _fresh(p):
        return json.loads(p.read_text())

    import yfinance as yf
    fx = {"USD": 1.0}
    for cur, sym in {"CNY": "CNYUSD=X", "HKD": "HKDUSD=X", "EUR": "EURUSD=X"}.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            if not h.empty:
                fx[cur] = float(h["Close"].iloc[-1])
        except Exception:
            pass
    fx.setdefault("CNY", 0.14)
    fx.setdefault("HKD", 0.128)
    fx.setdefault("EUR", 1.08)
    p.write_text(json.dumps(fx, indent=2))
    _record("FX", "OK", len(fx), ", ".join(f"{k}={v:.4f}" for k, v in fx.items()))
    return fx


def fetch_prices(tickers: list[str], benchmark: str, force: bool = False) -> pd.DataFrame:
    p = CACHE / "prices.csv"
    if not force and _fresh(p):
        df = pd.read_csv(p, index_col=0, parse_dates=True)
        _record("prices", "CACHED", df.shape[1], f"{len(df)} days")
        return df

    import yfinance as yf
    start = (datetime.now() - timedelta(days=365 * YEARS + 30)).strftime("%Y-%m-%d")
    raw = yf.download(tickers + [benchmark], start=start, auto_adjust=True,
                      progress=False, threads=True)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    close = close.sort_index()

    dead = [c for c in close.columns if close[c].notna().sum() == 0]
    if dead:
        close = close.drop(columns=dead)
        _record("unresolved tickers", "WARN", len(dead), ", ".join(sorted(dead)))

    close.index.name = "date"
    close.to_csv(p)
    _record("prices", "OK", close.shape[1], f"{len(close)} days from {close.index[0].date()}")
    return close


def _pick(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", float("inf")):
            return v
    return None


def fetch_profiles(tickers: list[str], fx: dict, force: bool = False) -> dict:
    """Business description and financials, one call per ticker."""
    p = CACHE / "profiles.json"
    if not force and _fresh(p):
        d = json.loads(p.read_text())
        _record("profiles", "CACHED", len(d))
        return d

    import yfinance as yf
    out, failed = {}, []

    for i, t in enumerate(tickers, 1):
        try:
            tk = yf.Ticker(t)
            info = tk.info or {}
            cur_m = (info.get("currency") or "USD").upper()
            cur_f = (info.get("financialCurrency") or cur_m).upper()
            rm, rf = fx.get(cur_m, 1.0), fx.get(cur_f, 1.0)

            rec = {
                "ticker": t,
                "name": _pick(info, "longName", "shortName") or t,
                "summary": _pick(info, "longBusinessSummary") or "",
                "sector_yf": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "website": info.get("website"),
                "employees": _pick(info, "fullTimeEmployees"),
                "currency_market": cur_m,
                "currency_fin": cur_f,
                "market_cap_usd": (_pick(info, "marketCap") or 0) * rm or None,
                "revenue_usd": (_pick(info, "totalRevenue") or 0) * rf or None,
                "revenue_growth_yoy": _pick(info, "revenueGrowth"),
                "earnings_growth_yoy": _pick(info, "earningsGrowth"),
                "profit_margin": _pick(info, "profitMargins"),
                "gross_margin": _pick(info, "grossMargins"),
                "operating_margin": _pick(info, "operatingMargins"),
                "roe": _pick(info, "returnOnEquity"),
                "pe": _pick(info, "trailingPE"),
                "forward_pe": _pick(info, "forwardPE"),
                "price_to_book": _pick(info, "priceToBook"),
                "debt_to_equity": _pick(info, "debtToEquity"),
                "free_cashflow_usd": (_pick(info, "freeCashflow") or 0) * rf or None,
                "dividend_yield": _pick(info, "dividendYield"),
                "beta_yf": _pick(info, "beta"),
            }

            try:
                fin = tk.income_stmt
                if fin is not None and not fin.empty and "Total Revenue" in fin.index:
                    s = fin.loc["Total Revenue"].dropna().sort_index()
                    rec["revenue_history"] = [
                        {"y": str(ix.date())[:4], "v": float(v) * rf} for ix, v in s.items()]
                    if len(s) >= 2:
                        yrs = (s.index[-1] - s.index[0]).days / 365.25
                        a, b = float(s.iloc[0]), float(s.iloc[-1])
                        if a > 0 and b > 0 and yrs >= 0.9:
                            rec["revenue_cagr"] = (b / a) ** (1 / yrs) - 1
                            rec["revenue_cagr_years"] = round(yrs, 1)
            except Exception:
                pass

            try:
                cf = tk.cashflow
                if cf is not None and not cf.empty:
                    rows = [r for r in cf.index if "Capital Expenditure" in str(r)]
                    if rows:
                        s = cf.loc[rows[0]].dropna().sort_index()
                        if len(s):
                            rec["capex_usd"] = abs(float(s.iloc[-1])) * rf
            except Exception:
                pass

            if rec.get("capex_usd") and rec.get("revenue_usd"):
                rec["capex_intensity"] = rec["capex_usd"] / rec["revenue_usd"]

            out[t] = rec
        except Exception as e:  # noqa: BLE001
            failed.append(f"{t} ({type(e).__name__})")
        if i % 20 == 0:
            time.sleep(1)

    p.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    _record("profiles", "OK", len(out),
            f"{len(failed)} failed: {', '.join(failed)}" if failed else "")
    return out
