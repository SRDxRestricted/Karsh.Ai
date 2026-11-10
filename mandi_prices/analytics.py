"""
analytics.py — Pure analytics for the mandi price dashboard.

Rules for this module:
  * no Streamlit imports (so it stays unit-testable)
  * no rendering, no HTML
  * every function tolerates an empty DataFrame and returns an empty/None result
"""

from __future__ import annotations

from datetime import date

import pandas as pd

# Volatility bands based on the coefficient of variation (stdev / mean).
LOW_VOLATILITY_CV = 3.0
HIGH_VOLATILITY_CV = 8.0

SELL_PERCENTILE = 70.0
HOLD_PERCENTILE = 30.0


# ── Filtering ───────────────────────────────────────────────────────────────


def filter_prices(
    df: pd.DataFrame,
    crop: str | None = None,
    districts: list[str] | str | None = None,
    start=None,
    end=None,
    include_future: bool = False,
    as_of: date | None = None,
) -> pd.DataFrame:
    """Apply the dashboard's global filters in one place.

    Unless ``include_future`` is set, rows dated after ``as_of`` (default: today)
    are dropped so synthetic future rows are never presented as history.
    """
    if df is None or df.empty:
        return df.iloc[0:0] if df is not None else pd.DataFrame()

    out = df

    if crop:
        crops = [crop] if isinstance(crop, str) else list(crop)
        out = out[out["crop"].isin(crops)]

    if districts:
        names = [districts] if isinstance(districts, str) else list(districts)
        out = out[out["district"].isin(names)]

    if start is not None:
        out = out[out["date"] >= pd.Timestamp(start)]
    if end is not None:
        out = out[out["date"] <= pd.Timestamp(end)]

    if not include_future:
        cutoff = pd.Timestamp(as_of or date.today())
        out = out[out["date"] <= cutoff]

    return out.sort_values(["date", "district"]).reset_index(drop=True)


# ── Aggregation ─────────────────────────────────────────────────────────────


def daily_average(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse selected districts into one row per date (mean modal price)."""
    if df is None or df.empty:
        return pd.DataFrame(
            columns=["date", "modal_price", "min_price", "max_price", "districts", "observations"]
        )

    return (
        df.groupby("date", as_index=False)
        .agg(
            modal_price=("modal_price", "mean"),
            min_price=("min_price", "mean"),
            max_price=("max_price", "mean"),
            districts=("district", "nunique"),
            observations=("modal_price", "size"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )


def price_series(df: pd.DataFrame, rolling: tuple[int, ...] = (7, 30)) -> pd.DataFrame:
    """Per-district price series with rolling means computed inside each district."""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.sort_values(["district", "date"]).copy()
    for window in rolling:
        out[f"ma_{window}"] = out.groupby("district")["modal_price"].transform(
            lambda series: series.rolling(window, min_periods=1).mean()
        )
    return out.reset_index(drop=True)


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Month-by-month average, low and high for the selected slice."""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    out["period"] = out["date"].dt.strftime("%Y-%m")
    summary = (
        out.groupby("period", as_index=False)
        .agg(
            avg_modal=("modal_price", "mean"),
            min_price=("min_price", "min"),
            max_price=("max_price", "max"),
            observations=("modal_price", "size"),
        )
        .sort_values("period")
    )
    return summary.reset_index(drop=True)


# ── Statistics ──────────────────────────────────────────────────────────────


def volatility_label(cv: float | None) -> str:
    if cv is None:
        return "Unknown"
    if cv < LOW_VOLATILITY_CV:
        return "Low"
    if cv < HIGH_VOLATILITY_CV:
        return "Moderate"
    return "High"


def window_stats(df: pd.DataFrame, days: int | None = None, as_of=None) -> dict:
    """Min / max / mean / median / stdev / CV for the selected slice."""
    empty = {
        "count": 0,
        "min": None,
        "max": None,
        "mean": None,
        "median": None,
        "stdev": None,
        "cv": None,
        "volatility": "Unknown",
        "start": None,
        "end": None,
    }
    if df is None or df.empty:
        return empty

    subset = df
    if days is not None:
        end = pd.Timestamp(as_of) if as_of is not None else df["date"].max()
        subset = df[(df["date"] > end - pd.Timedelta(days=days)) & (df["date"] <= end)]

    if subset.empty:
        return empty

    prices = subset["modal_price"].astype(float)
    mean = float(prices.mean())
    stdev = float(prices.std(ddof=0)) if len(prices) > 1 else 0.0
    cv = (stdev / mean * 100) if mean else None

    return {
        "count": int(len(prices)),
        "min": float(prices.min()),
        "max": float(prices.max()),
        "mean": mean,
        "median": float(prices.median()),
        "stdev": stdev,
        "cv": cv,
        "volatility": volatility_label(cv),
        "start": subset["date"].min().date(),
        "end": subset["date"].max().date(),
    }


def latest_snapshot(df: pd.DataFrame, lookback_days: int = 30, as_of=None) -> dict:
    """Latest price plus change versus the nearest observation at/behind the lookback.

    Uses nearest-available-date rather than exact calendar arithmetic because the
    dataset has multi-month gaps (e.g. Coconut has no Apr-Jun data).
    """
    empty = {
        "price": None,
        "date": None,
        "prev_price": None,
        "prev_date": None,
        "change": None,
        "change_pct": None,
        "lookback_days": lookback_days,
    }
    daily = daily_average(df)
    if daily.empty:
        return empty

    cutoff = pd.Timestamp(as_of) if as_of is not None else daily["date"].max()
    current = daily[daily["date"] <= cutoff]
    if current.empty:
        return empty

    latest = current.iloc[-1]
    target = latest["date"] - pd.Timedelta(days=lookback_days)
    prior = daily[daily["date"] <= target]
    prev = prior.iloc[-1] if not prior.empty else None

    change = float(latest["modal_price"] - prev["modal_price"]) if prev is not None else None
    change_pct = (
        change / float(prev["modal_price"]) * 100
        if prev is not None and float(prev["modal_price"]) != 0
        else None
    )

    return {
        "price": float(latest["modal_price"]),
        "date": latest["date"].date(),
        "prev_price": float(prev["modal_price"]) if prev is not None else None,
        "prev_date": prev["date"].date() if prev is not None else None,
        "change": change,
        "change_pct": change_pct,
        "lookback_days": lookback_days,
    }


# ── Market comparison ───────────────────────────────────────────────────────


def district_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Average price per district with premium over the cheapest market.

    ``premium_pct`` compares average modal prices across the whole window.
    ``avg_daily_premium`` is the more useful number: the mean, over each trading
    day, of how much this district fetched above that day's cheapest district.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    compare = (
        df.groupby("district", as_index=False)
        .agg(
            avg_modal=("modal_price", "mean"),
            min_modal=("modal_price", "min"),
            max_modal=("modal_price", "max"),
            avg_spread=("price_spread", "mean"),
            days=("date", "nunique"),
        )
        .sort_values("avg_modal", ascending=False)
        .reset_index(drop=True)
    )

    cheapest = float(compare["avg_modal"].min())
    compare["premium_pct"] = (
        (compare["avg_modal"] - cheapest) / cheapest * 100 if cheapest else 0.0
    )

    daily_min = df.groupby("date")["modal_price"].transform("min")
    daily_premium = (
        df.assign(_premium=df["modal_price"] - daily_min)
        .groupby("district")["_premium"]
        .mean()
    )
    compare["avg_daily_premium"] = compare["district"].map(daily_premium).fillna(0.0)

    compare.insert(0, "rank", range(1, len(compare) + 1))
    return compare


def best_market(df: pd.DataFrame) -> dict | None:
    """Highest-average district, with context for the UI."""
    compare = district_comparison(df)
    if compare.empty:
        return None

    top = compare.iloc[0]
    cheapest = compare.iloc[-1]
    return {
        "district": str(top["district"]),
        "avg_modal": float(top["avg_modal"]),
        "min_modal": float(top["min_modal"]),
        "max_modal": float(top["max_modal"]),
        "premium_pct": float(top["premium_pct"]),
        "avg_daily_premium": float(top["avg_daily_premium"]),
        "cheapest_district": str(cheapest["district"]),
        "cheapest_avg": float(cheapest["avg_modal"]),
        "spread": float(top["avg_daily_premium"]),
        "markets_compared": int(len(compare)),
    }


# ── Sell signal ─────────────────────────────────────────────────────────────


def sell_signal(df: pd.DataFrame, lookback_days: int = 90, as_of=None) -> dict | None:
    """Percentile of the current price inside the trailing window.

    This is a transparent heuristic, not a forecast or financial advice.
    """
    daily = daily_average(df)
    if daily.empty:
        return None

    cutoff = pd.Timestamp(as_of) if as_of is not None else daily["date"].max()
    current = daily[daily["date"] <= cutoff]
    if current.empty:
        return None

    window = current[current["date"] > cutoff - pd.Timedelta(days=lookback_days)]
    if window.empty:
        window = current

    latest = float(window["modal_price"].iloc[-1])
    low = float(window["modal_price"].min())
    high = float(window["modal_price"].max())

    if high == low:
        return {
            "percentile": None,
            "label": "Insufficient variation",
            "tone": "flat",
            "current": latest,
            "window_min": low,
            "window_max": high,
            "lookback_days": lookback_days,
            "observations": int(len(window)),
            "rationale": (
                f"Prices have not moved in the last {lookback_days} days "
                f"(₹{low:,.0f}), so there is nothing to time."
            ),
        }

    percentile = (latest - low) / (high - low) * 100

    if percentile >= SELL_PERCENTILE:
        label, tone = "Good time to sell", "up"
    elif percentile >= HOLD_PERCENTILE:
        label, tone = "Average — keep monitoring", "flat"
    else:
        label, tone = "Low price — hold if you can store", "down"

    return {
        "percentile": float(percentile),
        "label": label,
        "tone": tone,
        "current": latest,
        "window_min": low,
        "window_max": high,
        "lookback_days": lookback_days,
        "observations": int(len(window)),
        "rationale": (
            f"Today's ₹{latest:,.0f} sits at the {percentile:.0f}th percentile of the "
            f"last {lookback_days} days (₹{low:,.0f}–₹{high:,.0f}, "
            f"{len(window)} observations)."
        ),
    }


# ── Cross-crop table ────────────────────────────────────────────────────────


def crop_price_table(df: pd.DataFrame, as_of=None) -> pd.DataFrame:
    """Latest price per crop plus its 30-day change (computed within each crop)."""
    if df is None or df.empty:
        return pd.DataFrame()

    rows = []
    for crop, group in df.groupby("crop"):
        snapshot = latest_snapshot(group, lookback_days=30, as_of=as_of)
        if snapshot["price"] is None:
            continue
        rows.append(
            {
                "crop": crop,
                "latest_date": snapshot["date"],
                "modal_price": snapshot["price"],
                "change_30d": snapshot["change"],
                "change_30d_pct": snapshot["change_pct"],
                "districts": int(group["district"].nunique()),
                "observations": int(len(group)),
            }
        )

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .sort_values("modal_price", ascending=False)
        .reset_index(drop=True)
    )
