"""
Crop price TREND ESTIMATOR (rise / fall / stable).

Works for ANY crop: it only needs a (date, price) history for that crop.
Method (deliberately simple & explainable):
  1. Aggregate prices to monthly averages.
  2. Fit Ridge regression on log(price) using a linear trend (+ yearly seasonality
     when >= 24 months of data) over the most recent 48 months.
  3. Project `horizon` months ahead with an ~80% uncertainty band.
  4. Walk-forward backtest on the crop's own history -> honest accuracy numbers.

This is an ESTIMATE, not a guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

RISE_FALL_THRESHOLD = 0.03   # +/-3% counts as a real move; inside that = "stable"
MIN_MONTHS = 8               # below this we refuse to forecast
SEASON_MIN_MONTHS = 24       # need two yearly cycles before using seasonality
MAX_WINDOW = 48              # only the last 4 years influence the trend
Z80 = 1.2816                 # z-score for an 80% interval
MIN_SIGMA = 0.03             # never claim less than 3% monthly noise

DISCLAIMER = (
    "This is a statistical ESTIMATE based on past prices only. It does not know about "
    "weather, policy, export rules or sudden market shocks. Do not treat it as a "
    "guarantee or as financial advice."
)


class InsufficientDataError(ValueError):
    pass


@dataclass
class ForecastResult:
    crop: str
    horizon: int
    history: pd.DataFrame            # date, price (monthly)
    forecast: pd.DataFrame           # date, price, low, high
    last_price: float
    target_price: float
    pct_change: float                # fraction, e.g. 0.052 = +5.2%
    direction: str                   # "RISE" | "FALL" | "STABLE"
    confidence: str                  # "High" | "Medium" | "Low"
    used_seasonality: bool
    n_months: int
    backtest: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    disclaimer: str = DISCLAIMER


# ------------------------------------------------------------------ helpers
def to_monthly(df: pd.DataFrame) -> pd.Series:
    d = df[["date", "price"]].copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["price"] = pd.to_numeric(d["price"], errors="coerce")
    d = d.dropna()
    d = d[d["price"] > 0]
    if d.empty:
        return pd.Series(dtype=float)
    s = d.set_index("date")["price"].resample("MS").mean()
    return s.interpolate(limit=2, limit_area="inside").dropna()


def _features(dates, origin, season: bool) -> np.ndarray:
    t = np.array([(d.year - origin.year) * 12 + (d.month - origin.month) for d in dates],
                 dtype=float) / 12.0
    cols = [t]
    if season:
        ang = 2 * np.pi * np.array([d.month for d in dates]) / 12.0
        cols += [np.sin(ang), np.cos(ang)]
    return np.column_stack(cols)


def _fit_predict(series: pd.Series, future_dates, season: bool):
    y = np.log(series.values)
    X = _features(series.index, series.index[0], season)
    model = Ridge(alpha=0.5).fit(X, y)
    sigma = float(np.std(y - model.predict(X)))
    mu = model.predict(_features(future_dates, series.index[0], season))
    return mu, sigma


def _classify(change: float) -> str:
    if change > RISE_FALL_THRESHOLD:
        return "RISE"
    if change < -RISE_FALL_THRESHOLD:
        return "FALL"
    return "STABLE"


def _backtest(series: pd.Series, horizon: int) -> dict:
    """Walk-forward: pretend we were at each past month, predict `horizon` ahead, compare."""
    n = len(series)
    hits, naive_hits, apes = [], [], []
    start = max(MIN_MONTHS, n - 12 - horizon)
    for i in range(start, n - horizon + 1):
        train = series.iloc[:i].iloc[-MAX_WINDOW:]
        target_date = series.index[i + horizon - 1]
        season = len(train) >= SEASON_MIN_MONTHS
        pred = float(np.exp(_fit_predict(train, pd.DatetimeIndex([target_date]), season)[0][0]))
        base = float(train.iloc[-2:].mean())
        actual = float(series.iloc[i + horizon - 1])
        actual_dir = _classify(actual / base - 1)
        hits.append(_classify(pred / base - 1) == actual_dir)
        naive_hits.append(actual_dir == "STABLE")      # baseline: "nothing will change"
        apes.append(abs(pred - actual) / actual)
    if len(hits) < 3:
        return {}
    return {
        "n_tests": len(hits),
        "directional_accuracy": float(np.mean(hits)),
        "baseline_accuracy": float(np.mean(naive_hits)),
        "mape": float(np.mean(apes)),
    }


# --------------------------------------------------------------------- main
def forecast_price_trend(df: pd.DataFrame, crop: str, horizon: int = 3) -> ForecastResult:
    horizon = int(min(max(horizon, 1), 12))
    full = to_monthly(df)
    if len(full) < MIN_MONTHS:
        raise InsufficientDataError(
            f"Only {len(full)} months of price history for {crop}; need at least {MIN_MONTHS}."
        )
    series = full.iloc[-MAX_WINDOW:]
    season = len(series) >= SEASON_MIN_MONTHS

    future = pd.date_range(series.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    mu, sigma = _fit_predict(series, future, season)
    sigma = max(sigma, MIN_SIGMA)
    steps = np.arange(1, horizon + 1)
    width = Z80 * sigma * np.sqrt(steps)
    fc = pd.DataFrame({
        "date": future,
        "price": np.exp(mu),
        "low": np.exp(mu - width),
        "high": np.exp(mu + width),
    })

    base = float(series.iloc[-2:].mean())
    target = float(fc["price"].iloc[-1])
    pct = target / base - 1
    direction = _classify(pct)

    bt = _backtest(series, horizon) if len(series) >= MIN_MONTHS + horizon + 3 else {}

    # ---- confidence (simple, transparent scoring) ----
    score = 0
    score += 1 if len(series) >= 24 else 0
    score += 1 if len(series) >= 36 else 0
    if bt:
        score += 1 if bt["directional_accuracy"] >= 0.60 else 0
        score += 1 if bt["directional_accuracy"] > bt["baseline_accuracy"] else 0
    lo_chg, hi_chg = fc["low"].iloc[-1] / base - 1, fc["high"].iloc[-1] / base - 1
    if direction == "RISE":
        score += 1 if lo_chg > 0 else 0
    elif direction == "FALL":
        score += 1 if hi_chg < 0 else 0
    else:
        score += 1 if (lo_chg > -0.10 and hi_chg < 0.10) else 0
    confidence = "High" if score >= 4 else "Medium" if score >= 2 else "Low"
    if len(series) < 12:
        confidence = "Low"

    notes = []
    if len(series) < 24:
        notes.append("Less than 2 years of data: seasonal patterns were NOT used.")
    if not bt:
        notes.append("Not enough history to backtest this crop, so accuracy is unknown.")
    elif bt["directional_accuracy"] <= bt["baseline_accuracy"]:
        notes.append("On past data this model did not beat simply assuming 'no change'.")
    if direction != "STABLE" and ((direction == "RISE" and lo_chg <= 0) or (direction == "FALL" and hi_chg >= 0)):
        notes.append("The uncertainty range includes the opposite direction.")

    return ForecastResult(
        crop=crop, horizon=horizon,
        history=pd.DataFrame({"date": series.index, "price": series.values}),
        forecast=fc, last_price=base, target_price=target, pct_change=pct,
        direction=direction, confidence=confidence, used_seasonality=season,
        n_months=len(series), backtest=bt, notes=notes,
    )
