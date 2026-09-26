"""How a Hong Kong-listed company relates to three different markets.

Every name here trades in Hong Kong, but that says little about what actually
drives it. Three regressions of weekly returns answer it:

* **US** — against the S&P 500. Global risk appetite and the dollar cycle.
* **Hong Kong** — against the Hang Seng. Local liquidity and the flows that
  actually clear the trade.
* **Mainland China** — against the CSI 300. Beijing's policy cycle and domestic
  sentiment.

The **mainland-minus-Hong-Kong gap** is the interesting number, and the reason
this tool exists. Two companies on the same exchange can be entirely different
assets: one moves with Shanghai because its customers, revenue and regulator are
mainland, while another moves with global money because it is a Hong Kong
property company or a multinational that happens to list here. The gap separates
them without anyone having to assert a narrative.

Weekly rather than daily returns throughout. Hong Kong closes before New York
opens, so daily co-movement with the S&P understates the relationship for
mechanical reasons, and the mainland trades a different holiday calendar again.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_WEEKS = 40


def _weekly(s: pd.Series) -> pd.Series:
    return np.log(s.resample("W-FRI").last().dropna()).diff().dropna()


def _regress(y: pd.Series, x: pd.Series) -> dict:
    j = pd.concat([y, x], axis=1, join="inner").dropna()
    j.columns = ["y", "x"]
    if len(j) < MIN_WEEKS:
        return {"beta": None, "correlation": None, "r_squared": None,
                "n_weeks": int(len(j))}
    xv, yv = j["x"].to_numpy(), j["y"].to_numpy()
    var = xv.var()
    if var <= 0:
        return {"beta": None, "correlation": None, "r_squared": None,
                "n_weeks": int(len(j))}
    corr = float(np.corrcoef(xv, yv)[0, 1])
    return {"beta": float(np.cov(xv, yv)[0, 1] / var),
            "correlation": corr,
            "r_squared": float(corr ** 2),
            "n_weeks": int(len(j))}



def _multi_regress(y: pd.Series, xs: dict[str, pd.Series]) -> dict:
    """Regress the stock on all three indices at once.

    The scenario tool needs this rather than the three single-index betas.
    Those are each measured with the other two ignored, so the same worldwide
    risk-on week is counted in all three; adding them up to answer "if the S&P
    does X and the Hang Seng does Y" would double- and triple-count the move.
    A joint fit apportions it — each coefficient is the effect of that index
    holding the other two still, which is the question the tool actually asks.

    The cost is that correlated regressors make individual coefficients less
    stable, and one can even come out negative. That is real, not a bug: it
    says the index adds nothing once the others are known.
    """
    cols = [k for k, v in xs.items() if v is not None and len(v)]
    if not cols:
        return {}
    frame = pd.concat([y.rename("y")] + [xs[k].rename(k) for k in cols],
                      axis=1, join="inner").dropna()
    if len(frame) < MIN_WEEKS:
        return {}

    Y = frame["y"].to_numpy()
    X = frame[cols].to_numpy()
    A = np.column_stack([np.ones(len(X)), X])       # intercept + factors
    try:
        coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    except np.linalg.LinAlgError:
        return {}

    fitted = A @ coef
    resid = Y - fitted
    ss_res = float((resid ** 2).sum())
    ss_tot = float(((Y - Y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None

    return {
        "betas": {k: float(coef[i + 1]) for i, k in enumerate(cols)},
        "alpha_weekly": float(coef[0]),
        "r_squared": r2,
        # Weekly standard deviation of what the indices do NOT explain. It is
        # what turns a single projected price into an honest range.
        "residual_vol_weekly": float(resid.std(ddof=len(cols) + 1)),
        "n_weeks": int(len(frame)),
        "factors": cols,
    }


def analyse(px: pd.Series, benchmarks: pd.DataFrame) -> dict:
    y = _weekly(px.dropna())
    out: dict = {}
    for key in ("us", "hk", "cn"):
        out[key] = (_regress(y, _weekly(benchmarks[key].dropna()))
                    if key in benchmarks.columns else
                    {"beta": None, "correlation": None, "r_squared": None, "n_weeks": 0})

    cn, hk = out["cn"], out["hk"]
    gap = None
    if cn["r_squared"] is not None and hk["r_squared"] is not None:
        gap = cn["r_squared"] - hk["r_squared"]

    out["gap"] = {
        "value": gap,
        "verdict": _gap_verdict(gap, cn, hk),
    }
    out["driver"] = _driver(out)
    out["joint"] = _multi_regress(
        y, {k: (_weekly(benchmarks[k].dropna()) if k in benchmarks.columns else None)
            for k in ("us", "hk", "cn")})
    return out


def _gap_verdict(gap, cn, hk) -> str:
    if gap is None:
        return "Not enough overlapping history to compare."
    if gap > 0.08:
        return ("Tracks the mainland more closely than Hong Kong. Its price is set by "
                "Chinese domestic sentiment and policy, not by local Hong Kong flows.")
    if gap < -0.08:
        return ("Tracks Hong Kong more closely than the mainland. It lists in China's "
                "orbit but trades on Hong Kong and global money.")
    return ("Moves with Hong Kong and the mainland about equally, with no clear separation "
            "between the two.")


def _driver(o: dict) -> dict:
    """Which market explains the most of this stock's weekly movement."""
    scored = [(k, o[k]["r_squared"]) for k in ("us", "hk", "cn")
              if o[k].get("r_squared") is not None]
    if not scored:
        return {"market": None, "label": "Unclear", "r_squared": None}
    scored.sort(key=lambda kv: kv[1], reverse=True)
    top, r2 = scored[0]
    names = {"us": "the US market", "hk": "the Hong Kong market",
             "cn": "the mainland Chinese market"}
    if r2 < 0.05:
        return {"market": None,
                "label": "Moves on its own", "r_squared": r2,
                "text": "No index explains much of its movement. It trades on "
                        "company-specific news rather than any market."}
    # .capitalize() would lowercase the rest — "The hong kong market".
    lead = names[top][0].upper() + names[top][1:]
    return {"market": top, "label": f"Driven by {names[top]}", "r_squared": r2,
            "text": f"{lead} explains {r2*100:.0f}% of its "
                    "weekly movement, more than either of the others."}
