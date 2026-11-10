"""
loader.py — Load, normalise, validate and cache the Kerala mandi price dataset.

Single source of truth for price data. Both the crop predictor and the mandi
price dashboard read through this module.

Deliberately contains no analytics: everything here answers "what is a clean,
trustworthy price table?" and nothing else.
"""

from __future__ import annotations

import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "mandi_prices.csv")

# Raw CSV header -> normalised column name
COLUMN_MAP = {
    "Date": "date",
    "District": "district",
    "Market": "market",
    "Commodity": "crop",
    "Variety": "variety",
    "Min_Price": "min_price",
    "Max_Price": "max_price",
    "Modal_Price": "modal_price",
}

PRICE_COLUMNS = ["min_price", "max_price", "modal_price"]
TEXT_COLUMNS = ["district", "market", "crop", "variety"]
KEY_COLUMNS = ["date", "district", "market", "crop", "variety"]


def _read_dataframe(path: str) -> pd.DataFrame:
    """Read the raw CSV and return a normalised, typed DataFrame."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Mandi price dataset not found at: {path}")

    raw = pd.read_csv(path)

    missing = [column for column in COLUMN_MAP if column not in raw.columns]
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    df = raw.rename(columns=COLUMN_MAP)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in PRICE_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in TEXT_COLUMNS:
        df[column] = df[column].astype(str).str.strip()

    # Drop rows we cannot analyse rather than letting NaNs poison the charts.
    df = df.dropna(subset=["date", *PRICE_COLUMNS]).reset_index(drop=True)

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.month_name()
    df["week"] = df["date"].dt.isocalendar().week.astype(int)
    df["dayofweek"] = df["date"].dt.day_name()
    df["price_spread"] = df["max_price"] - df["min_price"]
    df["spread_pct"] = (
        df["price_spread"] / df["modal_price"].mask(df["modal_price"] == 0)
    ) * 100

    return df.sort_values(["date", "crop", "district"]).reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_price_data(path: str | None = None) -> pd.DataFrame:
    """Cached loader. Re-reads at most once per hour per process."""
    return _read_dataframe(path or DEFAULT_DATA_PATH)


# ── Coverage helpers ────────────────────────────────────────────────────────
# The dataset does not cover every crop for the whole year, so the UI must
# derive its date bounds from the data instead of assuming Jan-Dec.


def crop_windows(df: pd.DataFrame) -> dict[str, tuple[date, date]]:
    """Map each crop to the (first, last) date it actually has data for."""
    if df.empty:
        return {}
    windows = {
        str(crop): (group["date"].min().date(), group["date"].max().date())
        for crop, group in df.groupby("crop")
    }
    return dict(sorted(windows.items()))


def districts_for_crop(df: pd.DataFrame, crop: str) -> list[str]:
    """Districts that report prices for a given crop."""
    subset = df.loc[df["crop"] == crop, "district"]
    return sorted(subset.dropna().unique().tolist())


def latest_data_date(df: pd.DataFrame) -> date | None:
    if df.empty:
        return None
    return df["date"].max().date()


def coverage_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Crop x district observation counts. Zeros surface missing coverage."""
    if df.empty:
        return pd.DataFrame()
    matrix = (
        df.pivot_table(
            index="crop",
            columns="district",
            values="modal_price",
            aggfunc="count",
            fill_value=0,
        )
        .astype(int)
        .sort_index()
    )
    matrix.index.name = "crop"
    matrix.columns.name = "district"
    return matrix


# ── Validation ──────────────────────────────────────────────────────────────


def _max_gap_days(df: pd.DataFrame) -> int:
    """Largest calendar gap between consecutive observations for any series."""
    largest = 0
    for _, group in df.groupby(["crop", "district"]):
        gaps = group["date"].sort_values().diff().dt.days.dropna()
        if not gaps.empty:
            largest = max(largest, int(gaps.max()))
    return largest


def validate_data(df: pd.DataFrame, as_of: date | None = None) -> dict:
    """Data-integrity report. Used by tests and the dashboard's health panel."""
    if df.empty:
        return {"rows": 0, "status": "empty"}

    price_ok = (df["min_price"] <= df["modal_price"]) & (
        df["modal_price"] <= df["max_price"]
    )
    cutoff = pd.Timestamp(as_of or date.today())

    return {
        "status": "ok" if price_ok.all() else "issues",
        "rows": int(len(df)),
        "crops": int(df["crop"].nunique()),
        "districts": int(df["district"].nunique()),
        "markets": int(df["market"].nunique()),
        "varieties": int(df["variety"].nunique()),
        "first_date": df["date"].min().date().isoformat(),
        "last_date": df["date"].max().date().isoformat(),
        "blank_cells": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated(subset=KEY_COLUMNS).sum()),
        "invalid_price_ranges": int((~price_ok).sum()),
        "rows_after_as_of": int((df["date"] > cutoff).sum()),
        "max_gap_days": _max_gap_days(df),
    }
