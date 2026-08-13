"""Parse HKEX's official List of Securities into a tradable equity universe.

The file carries 17,669 rows, but only ~2,800 are companies. The rest are
derivative warrants, callable bull/bear contracts and bonds — instruments, not
issuers, and nothing this tool says about a company applies to them.

HKEX stock codes are five-digit strings ("00700"); Yahoo wants four digits plus
a suffix ("0700.HK"). The GEM board runs in the 8000s and maps the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SECURITIES_FILE = ROOT / "ListOfSecurities.xlsx"

# Only these are operating companies. REITs and Investment Companies are
# included deliberately — they have boards, financials and a share price.
KEEP_SUBCATEGORIES = {
    "Equity Securities (Main Board)",
    "Equity Securities (GEM)",
    "Investment Companies",
}
KEEP_CATEGORIES = {"Equity", "Real Estate Investment Trusts"}


@dataclass(frozen=True)
class Security:
    code: str        # HKEX code, zero-padded five digits
    ticker: str      # yfinance symbol
    name: str        # HKEX short name
    board: str       # Main Board | GEM | REIT | Investment Company
    isin: str = ""
    lot: str = ""


def _board(sub: str, cat: str) -> str:
    if cat == "Real Estate Investment Trusts":
        return "REIT"
    if sub == "Equity Securities (GEM)":
        return "GEM"
    if sub == "Investment Companies":
        return "Investment Company"
    return "Main Board"


def load(path: Path | None = None) -> list[Security]:
    path = path or SECURITIES_FILE
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} not found. Download the List of Securities from HKEX "
            "and place it in the project root."
        )

    # Row 0 is a title, row 1 an 'Updated as at' stamp; the real header is row 2.
    df = pd.read_excel(path, skiprows=2)
    df.columns = [str(c).strip() for c in df.columns]

    cat = df["Category"].astype(str).str.strip()
    sub = df["Sub-Category"].astype(str).str.strip()
    keep = cat.isin(KEEP_CATEGORIES) & (sub.isin(KEEP_SUBCATEGORIES) |
                                        (cat == "Real Estate Investment Trusts"))
    df = df[keep]

    out: list[Security] = []
    seen: set[str] = set()
    for _, r in df.iterrows():
        raw = str(r["Stock Code"]).strip()
        try:
            n = int(float(raw))
        except (TypeError, ValueError):
            continue
        # Above 10000 sits the RMB-counter and structured space, not ordinary
        # equity lines.
        if not (1 <= n <= 9999):
            continue
        code = f"{n:05d}"
        if code in seen:
            continue
        seen.add(code)
        out.append(Security(
            code=code,
            ticker=f"{n:04d}.HK",
            name=str(r["Name of Securities"]).strip().title(),
            board=_board(sub.loc[_], cat.loc[_]) if _ in sub.index else "Main Board",
            isin=str(r.get("ISIN", "") or "").strip(),
            lot=str(r.get("Board Lot", "") or "").strip(),
        ))

    out.sort(key=lambda s: s.code)
    return out


def as_of(path: Path | None = None) -> str:
    """The 'Updated as at DD/MM/YYYY' stamp in the sheet's second row."""
    path = path or SECURITIES_FILE
    try:
        head = pd.read_excel(path, nrows=2, header=None)
        for v in head.to_numpy().ravel():
            s = str(v)
            if "Updated as at" in s:
                return s.replace("Updated as at", "").strip()
    except Exception:
        pass
    return ""
