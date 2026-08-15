"""Ingest for the full HKEX equity board.

Scale changes the approach. At ~2,800 companies, prices must come down in bulk
batches and profiles must be fetched concurrently, or a build takes hours. Both
caches are written to disk so a rebuild costs seconds.

Three benchmarks are needed because the whole point of the tool is comparing
them: the S&P 500 for the US, the Hang Seng for Hong Kong, and the CSI 300 for
the mainland. The first two come from Yahoo; the CSI 300 comes from AkShare,
because Yahoo has no reliable mainland index series.
"""

from __future__ import annotations

import json
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "hkcache"
CACHE.mkdir(parents=True, exist_ok=True)

# Committed profile coverage, so CI and a fresh clone do not start from zero.
# Refresh it with `python tools/update_seed.py`.
SEED = ROOT / "seed" / "profiles.json"

YEARS = 5
TTL_HOURS = 20
BATCH = 150
WORKERS = 12

# Profile fetching runs against Yahoo's quoteSummary endpoint, which is
# IP-rate-limited and cannot serve the whole board in one build. Asking for all
# 2,782 in a single run returns 401/429 for roughly three quarters of them, and
# retrying inside the same run recovers nothing — the limit is per IP and
# outlives the process.
#
# So each run takes a fixed slice instead, and the cache accumulates across
# runs. The nightly job therefore fills coverage in over several nights rather
# than failing loudly every night. Prices are unaffected: the bulk download uses
# a different endpoint and covers the whole board in one pass.
PROFILE_WORKERS = 4
PROFILE_PAUSE = 0.12      # seconds between requests, per worker
PROFILE_BUDGET = 450      # new profiles to attempt per run


LINEAGE: list[dict] = []

BENCHMARKS = {
    "us": {"symbol": "^GSPC", "label": "S&P 500", "source": "yfinance"},
    "hk": {"symbol": "^HSI", "label": "Hang Seng Index", "source": "yfinance"},
    "cn": {"symbol": "sh000300", "label": "CSI 300", "source": "akshare"},
}


def _record(dataset: str, status: str, n: int, note: str = "") -> None:
    LINEAGE.append({"dataset": dataset, "status": status, "n": n, "note": note,
                    "fetched_at": datetime.now().isoformat(timespec="seconds")})


def _fresh(p: Path) -> bool:
    return p.exists() and (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)
                           < timedelta(hours=TTL_HOURS))


def _start() -> str:
    return (datetime.now() - timedelta(days=365 * YEARS + 45)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------

def fetch_fx(force: bool = False) -> dict[str, float]:
    p = CACHE / "fx.json"
    if not force and _fresh(p):
        return json.loads(p.read_text())
    import yfinance as yf
    # HKD and CNY cover almost every issuer here, but not all of them: Manulife
    # reports in CAD, and with only three rates in the table its revenue was
    # converted at a silent 1.0 and published 1.387x too high. Anything a
    # company might actually report in belongs here.
    pairs = {"HKD": "HKDUSD=X", "CNY": "CNYUSD=X", "CAD": "CADUSD=X",
             "GBP": "GBPUSD=X", "EUR": "EURUSD=X", "SGD": "SGDUSD=X",
             "JPY": "JPYUSD=X", "AUD": "AUDUSD=X", "TWD": "TWDUSD=X",
             "KRW": "KRWUSD=X", "MOP": "MOPUSD=X", "RMB": "CNYUSD=X"}
    fx = {"USD": 1.0}
    for cur, sym in pairs.items():
        try:
            h = yf.Ticker(sym).history(period="5d")
            if not h.empty:
                fx[cur] = float(h["Close"].iloc[-1])
        except Exception:
            pass
    fx.setdefault("HKD", 0.128)
    fx.setdefault("CNY", 0.14)
    fx.setdefault("CAD", 0.72)
    p.write_text(json.dumps(fx, indent=2))
    _record("FX", "OK", len(fx))
    return fx


def fetch_benchmarks(force: bool = False) -> pd.DataFrame:
    p = CACHE / "benchmarks.csv"
    if not force and _fresh(p):
        df = pd.read_csv(p, index_col=0, parse_dates=True)
        _record("benchmarks", "CACHED", df.shape[1])
        return df

    import yfinance as yf
    cols = {}

    raw = yf.download([BENCHMARKS["us"]["symbol"], BENCHMARKS["hk"]["symbol"]],
                      start=_start(), auto_adjust=True, progress=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    for key in ("us", "hk"):
        sym = BENCHMARKS[key]["symbol"]
        if sym in close.columns:
            s = close[sym].dropna()
            if len(s):
                cols[key] = s
                _record(f"benchmark {BENCHMARKS[key]['label']}", "OK", len(s))
            else:
                _record(f"benchmark {BENCHMARKS[key]['label']}", "EMPTY", 0)

    # CSI 300 — the mainland leg. AkShare's index endpoint is reachable even
    # though its A-share equity endpoints are geo-blocked here (they sit on
    # different hosts). If it fails, the mainland column is simply absent
    # rather than silently substituted with something else.
    try:
        import akshare as ak
        d = ak.stock_zh_index_daily(symbol=BENCHMARKS["cn"]["symbol"])
        d["date"] = pd.to_datetime(d["date"])
        s = d.set_index("date")["close"].sort_index()
        s = s[s.index >= _start()]
        cols["cn"] = s
        _record("benchmark CSI 300", "OK", len(s))
    except Exception as e:  # noqa: BLE001
        _record("benchmark CSI 300", "FAIL", 0, str(e)[:160])

    df = pd.DataFrame(cols).sort_index()
    df.index.name = "date"
    df.to_csv(p)
    return df


def _trim_prelisting(close: pd.DataFrame, vol: pd.DataFrame | None) -> pd.DataFrame:
    """Drop phantom bars that sit before a company actually started trading.

    Yahoo occasionally carries a placeholder bar months ahead of a listing:
    Midea (0300.HK) has one dated 2024-07-05 priced at 2.49 with zero volume,
    ten weeks before its real debut at 93.30. Ingested as a genuine price it
    becomes the base of every whole-history calculation — it published a
    +4,196% three-year return and 271% annualised volatility.

    Only *leading* zero-volume bars are removed. A zero-volume day is one on
    which nothing traded, so it carries no price information, and trimming from
    the front cannot disturb the mid-series gaps that thinly traded small caps
    legitimately have.
    """
    if vol is None:
        return close
    for col in close.columns:
        if col not in vol.columns:
            continue
        v = vol[col]
        traded = v.fillna(0) > 0
        if not traded.any():
            continue
        first_real = traded.idxmax()
        mask = (close.index < first_real)
        if mask.any():
            close.loc[mask, col] = float("nan")
    return close


def fetch_prices(tickers: list[str], force: bool = False) -> pd.DataFrame:
    """Five years of adjusted closes for the whole board, in batches."""
    p = CACHE / "prices.pkl"
    if not force and _fresh(p):
        df = pd.read_pickle(p)
        _record("prices", "CACHED", df.shape[1], f"{len(df)} days")
        return df

    import yfinance as yf
    frames, start = [], _start()

    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i:i + BATCH]
        try:
            raw = yf.download(chunk, start=start, auto_adjust=True,
                              progress=False, threads=True)
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"]
                vol = raw["Volume"] if "Volume" in raw.columns.get_level_values(0) else None
            else:
                close = raw[["Close"]] if "Close" in raw.columns else raw
                vol = raw[["Volume"]] if "Volume" in raw.columns else None
            if isinstance(close, pd.Series):
                close = close.to_frame(chunk[0])
            close = _trim_prelisting(close, vol)
            frames.append(close)
        except Exception as e:  # noqa: BLE001
            _record(f"price batch {i // BATCH}", "FAIL", 0, str(e)[:120])
        print(f"        prices {min(i + BATCH, len(tickers))}/{len(tickers)}", end="\r")

    if not frames:
        raise RuntimeError("no price data returned for any batch")

    df = pd.concat(frames, axis=1).sort_index()
    df = df.loc[:, ~df.columns.duplicated()]

    dead = [c for c in df.columns if df[c].notna().sum() < 30]
    if dead:
        df = df.drop(columns=dead)
        _record("thin or unlisted tickers", "WARN", len(dead),
                "fewer than 30 trading days of history; excluded")

    df.index.name = "date"
    df.to_pickle(p)
    _record("prices", "OK", df.shape[1], f"{len(df)} days from {df.index[0].date()}")
    return df


def _pick(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", float("inf")):
            return v
    return None


PROFILE_SCHEMA = 2


def _num(v):
    try:
        f = float(v)
        return f if f == f else None       # reject NaN
    except (TypeError, ValueError):
        return None


def _to_usd(value, rate):
    """Convert to USD, or return nothing at all.

    `rate` is None when the company reports in a currency we have no rate for.
    Returning the unconverted figure in that case is what published Manulife's
    CAD revenue as dollars; a blank is the only honest answer.
    """
    v = _num(value)
    if v is None or rate is None:
        return None
    return v * rate


def _dividend_yield(info: dict):
    """Dividend yield as a plain fraction, computed rather than guessed.

    `dividendYield` from Yahoo is a percentage — BYD returns 0.47 for 0.47%,
    confirmed against its own dividendRate 0.41 over a price of 88.25. That is
    indistinguishable by inspection from a fraction meaning 47%, and an earlier
    threshold rule got BYD wrong by a factor of a hundred.

    `dividendRate / price` has no such ambiguity: both are in the listing
    currency and the ratio is a fraction by construction. The percentage field
    is used only as a fallback, and only above 0.5 where the units cannot be
    mistaken.
    """
    rate = _num(info.get("dividendRate"))
    price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
    if rate and price and price > 0:
        return rate / price
    y = _num(info.get("dividendYield"))
    if y is None:
        return None
    return y / 100 if y > 0.5 else None    # below 0.5 the units are unknowable


def _legacy_yield(v):
    """Salvage a yield stored before yields were computed properly.

    The cache holds both forms — some records kept Yahoo's percentage (Tencent
    1.15 for 1.15%), most hold a proper fraction (ICBC 0.0486 for 4.86%) — and
    the field itself does not say which.

    Plausibility separates them. Read as a fraction, 0.47 would be a 47% yield,
    which no listed company pays; read as a percentage it is 0.47%, which BYD
    does pay. Read as a percentage, 0.0486 would be a 0.049% yield, which is
    absurdly small; as a fraction it is 4.86%, which is an ordinary bank. So
    values above the plausibility line are percentages and values below it are
    fractions.

    An earlier version drew that line at 0.5 and dropped everything beneath it,
    which was safe but threw away 361 correct yields — the whole high-yielding
    end of the board, banks and telecoms among them.
    """
    v = _num(v)
    if v is None or v <= 0:
        return None
    # Above 0.25 as a fraction would mean a yield over 25%: percentage form.
    frac = v / 100 if v > 0.25 else v
    # Anything still implying more than a 50% yield is not salvageable.
    return frac if 0 < frac <= 0.5 else None


def _officers(info: dict) -> list[dict]:
    """Named executives, most senior first.

    Yahoo returns them unranked and with wordy titles, so seniority is inferred
    from the title text — the CEO must be the first row for the panel to be
    worth reading.
    """
    import re

    def rank(title: str) -> int:
        t = (title or "").lower()
        # Split on non-letters so punctuation cannot hide a word. "Group CEO,
        # Member of the Board" tokenised on whitespace yields "ceo," which
        # never matched "ceo" — HSBC's group chief executive fell through to
        # the director branch and sorted last.
        words = set(re.findall(r"[a-z]+", t))

        # A divisional chief executive is not the company's chief executive.
        # The discriminator is whether the title says CEO *of something*:
        # "CEO of International Wealth" runs a division, "Group CEO, Member of
        # the Board" runs the company. Testing for the word "group" anywhere
        # fails, because the divisional title also mentions the Group
        # Management Board.
        divisional = bool(re.search(
            r"(?:ceo|chief executive(?:\s+officer)?)\s+of\s+"
            r"(?!the\s+(?:group|company)\b)", t))

        is_ceo = "chief executive" in t or "ceo" in words
        if is_ceo and not divisional:
            return 0
        if "chairman" in words or "chairwoman" in words:
            return 1
        if is_ceo:            # divisional CEO — below the chair, above the CFO
            return 2
        # President outranks the CFO. At PetroChina and China Merchants Bank
        # the upstream data lists no chairman or chief executive at all, and
        # the president is the person actually running the company — ranking
        # the CFO above them put the wrong name at the top.
        if "president" in words:
            return 3
        # "Chief Financial Markets Officer" is not a CFO; require the phrase to
        # end at "officer" or the bare acronym.
        if re.search(r"chief financial officer", t) or "cfo" in words:
            return 4
        if "chief operating" in t or "coo" in words:
            return 5
        if "chief" in words:
            return 6
        if "director" in words:
            return 7
        return 8

    out = []
    for o in (info.get("companyOfficers") or []):
        name = (o.get("name") or "").strip()
        title = (o.get("title") or "").strip()
        if not name:
            continue
        out.append({"name": " ".join(name.split()), "title": title,
                    "age": o.get("age"), "pay": o.get("totalPay"),
                    "_r": rank(title)})
    out.sort(key=lambda x: x["_r"])
    for o in out:
        o.pop("_r", None)
    return out[:8]


def fetch_profiles(tickers: list[str], fx: dict, force: bool = False,
                   budget: int | None = None) -> dict:
    """Company profiles, fetched incrementally and politely.

    Yahoo's quote endpoint issues a crumb per session and rejects sustained
    parallel load with `401 Invalid Crumb`. A first attempt at twelve workers
    returned only 24% of the board. The fix is threefold: fewer workers, a
    short pause between requests, and repeated passes that retry only what is
    still missing.

    The cache is **incremental** — whatever was successfully fetched before is
    kept and only the gaps are re-requested. Re-running the build therefore
    fills in coverage instead of starting from zero, which matters when the
    upstream throttles unpredictably.
    """
    p = CACHE / "profiles.json"

    # Start from the committed seed, then let the local cache override it.
    #
    # The working cache lives under data/, which is gitignored, so a CI runner
    # starts with nothing — and because the endpoint rate-limits by IP, it only
    # ever collects a couple of hundred before being cut off. The deployed site
    # was showing 182 profiles while this machine had 1,114. Committing the
    # accumulated profiles as a seed means every environment starts from the
    # same coverage and only fetches what is genuinely missing.
    have: dict = {}
    if SEED.exists():
        try:
            have.update(json.loads(SEED.read_text()))
        except Exception:
            pass
    if p.exists():
        try:
            have.update(json.loads(p.read_text()))
        except Exception:
            pass
    if not force and _fresh(p) and len(have) >= len(tickers) * 0.9:
        _record("profiles", "CACHED", len(have))
        return have

    import yfinance as yf
    done = {"n": 0}

    def one(t: str):
        try:
            info = yf.Ticker(t).info or {}
            if not info.get("shortName") and not info.get("longName"):
                return t, None
            cur_m = (info.get("currency") or "HKD").upper()
            cur_f = (info.get("financialCurrency") or cur_m).upper()
            # An unknown currency must not silently convert at 1.0 — that is
            # how CAD revenue got published as though it were dollars. Missing
            # rate means the figure is dropped, and the currency is recorded so
            # the gap is visible rather than invented.
            rm, rf = fx.get(cur_m), fx.get(cur_f)
            if rm is None:
                _record("unknown market currency", "WARN", 1, f"{t}: {cur_m}")
            if rf is None:
                _record("unknown reporting currency", "WARN", 1, f"{t}: {cur_f}")
            return t, {
                "name": _pick(info, "longName", "shortName"),
                "summary": _pick(info, "longBusinessSummary") or "",
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "country": info.get("country"),
                "city": info.get("city"),
                "website": info.get("website"),
                "employees": _pick(info, "fullTimeEmployees"),
                "currency": cur_m,
                "market_cap_usd": _to_usd(_pick(info, "marketCap"), rm),
                "revenue_usd": _to_usd(_pick(info, "totalRevenue"), rf),
                "revenue_growth": _pick(info, "revenueGrowth"),
                "profit_margin": _pick(info, "profitMargins"),
                # Yahoo returns exactly 0.0 for banks and insurers, where the
                # measure does not apply. Publishing "0.0% gross margin" for
                # ICBC states something false; absent is what is true.
                "gross_margin": (_pick(info, "grossMargins") or None) or None,
                "roe": _pick(info, "returnOnEquity"),
                "pe": _pick(info, "trailingPE"),
                "forward_pe": _pick(info, "forwardPE"),
                "price_to_book": _pick(info, "priceToBook"),
                "debt_to_equity": _pick(info, "debtToEquity"),
                "dividend_yield": _dividend_yield(info),
                "_v": PROFILE_SCHEMA,
                "free_cashflow_usd": _to_usd(_pick(info, "freeCashflow"), rf),
                "officers": _officers(info),
            }
        except Exception:
            return t, None
        finally:
            done["n"] += 1
            time.sleep(PROFILE_PAUSE)
            if done["n"] % 100 == 0:
                print(f"        profiles pass {done['pass']}: "
                      f"{done['n']}/{done['todo']}   ", end="\r")

    out = dict(have)
    missing = [t for t in tickers if t not in out]
    # Records written before the current schema are re-fetched too, after the
    # genuinely missing ones. That is how the dividend-yield fix reaches the
    # 1,100 companies already cached without re-fetching the whole board.
    stale = [t for t in tickers
             if t in out and out[t].get("_v", 0) < PROFILE_SCHEMA]
    # budget=0 on intraday quote refreshes: touching this endpoint every 30
    # minutes would exhaust the daily allowance and starve the nightly slice.
    limit = PROFILE_BUDGET if budget is None else budget
    batch = (missing + stale)[:limit]
    done["n"], done["pass"], done["todo"] = 0, 1, len(batch)

    if batch:
        with ThreadPoolExecutor(max_workers=PROFILE_WORKERS) as ex:
            for t, rec in ex.map(one, batch):
                if rec:
                    out[t] = rec
        p.write_text(json.dumps(out, ensure_ascii=False))

    # Records still on the old schema get their yield salvaged where the units
    # are unambiguous and blanked where they are not, until the refresh queue
    # reaches them.
    for rec in out.values():
        if rec.get("_v", 0) < PROFILE_SCHEMA:
            rec["dividend_yield"] = _legacy_yield(rec.get("dividend_yield"))

    gained = len(out) - len(have)
    still = len(tickers) - len(out)
    print(f"        profiles +{gained} this run · {len(out)}/{len(tickers)} "
          f"({len(out) / max(1, len(tickers)) * 100:.0f}%) · {still} outstanding   ")
    _record("profiles", "OK" if still == 0 else "PARTIAL", len(out),
            f"+{gained} this run; {still} still to fetch. Yahoo rate-limits this "
            f"endpoint, so coverage accumulates across runs.")
    return out
