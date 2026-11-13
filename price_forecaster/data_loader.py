"""
Data layer for the market-price trend estimator.

Price history lives in ONE csv: data/market_prices.csv
    columns:  date, crop, price            (price = modal price, Rs per quintal)
    optional: market, district

Real data can come from:
  1. A CSV you download from Agmarknet (agmarknet.gov.in) and rename to the columns above.
  2. fetch_daily_snapshot(): pulls today's mandi prices from data.gov.in and APPENDS
     them to the csv. Run it daily (cron / GitHub Action) to build history over time.

If a crop has no real history yet, load_prices() returns clearly-flagged DEMO data so
the feature still works for every crop. The UI must show a warning when source == "demo".
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "market_prices.csv"
CROP_PREDICTOR_DIR = ROOT / "crop_predictor"
HISTORICAL_DATA_PATH = CROP_PREDICTOR_DIR / "keralaCropDataset.txt"

# Fallback list if the crop predictor's data can't be read. EDIT to match your site.
DEFAULT_CROPS = [
    "Rice", "Coconut", "Banana", "Black Pepper", "Rubber", "Cardamom",
    "Ginger", "Turmeric", "Tapioca", "Arecanut", "Cashew", "Coffee",
    "Tea", "Vegetables",
]

# Different spellings -> one canonical name (used to match your crop names to mandi names)
ALIASES = {
    "paddy": "rice", "paddy(dhan)": "rice", "paddy (dhan)": "rice",
    "pepper": "black pepper", "pepper ungarbled": "black pepper",
    "coconut (copra)": "coconut", "copra": "coconut", "coconut seed": "coconut",
    "cassava": "tapioca", "tapioca": "tapioca",
    "ginger(dry)": "ginger", "ginger(green)": "ginger",
    "turmeric (raw)": "turmeric", "banana - green": "banana",
    "arecanut(betelnut/supari)": "arecanut", "areca nut": "arecanut",
    "cashewnuts": "cashew", "cashew nut": "cashew",
}

# Rough Rs/quintal levels, used ONLY for demo data so charts look plausible.
_DEMO_BASE = {
    "rice": 2400, "coconut": 3200, "banana": 3000, "black pepper": 55000,
    "rubber": 17000, "cardamom": 120000, "ginger": 6000, "turmeric": 9000,
    "tapioca": 2200, "arecanut": 45000, "cashew": 11000, "coffee": 30000,
    "tea": 25000, "vegetables": 3500,
}


def normalise_crop(name: str) -> str:
    n = str(name).strip().lower()
    return ALIASES.get(n, n)


# --------------------------------------------------------------------------- #
# Which crops does the site support?  (so the feature covers ALL of them)
# --------------------------------------------------------------------------- #
def get_supported_crops() -> list[str]:
    """
    Tries to read crop names from the crop_predictor folder (any csv/json that has a
    column/key like crop / label / commodity). Falls back to DEFAULT_CROPS.
    Also adds any crop that already has price history.
    """
    found: set[str] = set()
    keys = ("crop", "label", "commodity", "crop_name")

    if CROP_PREDICTOR_DIR.exists():
        for f in CROP_PREDICTOR_DIR.rglob("*.csv"):
            try:
                head = pd.read_csv(f, nrows=0)
                col = next((c for c in head.columns if c.strip().lower() in keys), None)
                if col:
                    vals = pd.read_csv(f, usecols=[col])[col].dropna().unique()
                    found.update(str(v).strip() for v in vals if 0 < len(str(v)) < 40)
            except Exception:
                continue
        for f in CROP_PREDICTOR_DIR.rglob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    # {"Rice": {...}, "Banana": {...}}  -> keys are crops
                    if all(isinstance(v, (dict, list)) for v in data.values()) and 2 <= len(data) <= 100:
                        found.update(str(k).strip() for k in data.keys())
                elif isinstance(data, list):
                    for row in data:
                        if isinstance(row, dict):
                            k = next((k for k in row if k.lower() in keys), None)
                            if k:
                                found.add(str(row[k]).strip())
            except Exception:
                continue

    if DATA_PATH.exists():
        try:
            found.update(pd.read_csv(DATA_PATH, usecols=["crop"])["crop"].dropna().unique())
        except Exception:
            pass

    crops = sorted({c.title() for c in found}) if len(found) >= 3 else list(DEFAULT_CROPS)
    return crops


# --------------------------------------------------------------------------- #
# Loading prices
# --------------------------------------------------------------------------- #
def _demo_series(crop: str, months: int = 60) -> pd.DataFrame:
    """Deterministic SYNTHETIC history (trend + yearly seasonality + noise). Not real."""
    key = normalise_crop(crop)
    seed = int(hashlib.md5(key.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    base = _DEMO_BASE.get(key, 1500 + (seed % 5000))
    end = pd.Timestamp(date.today()).to_period("M").to_timestamp()
    idx = pd.date_range(end=end, periods=months, freq="MS")
    t = np.arange(months)
    drift = rng.uniform(-0.002, 0.006)
    amp = rng.uniform(0.03, 0.12)
    phase = rng.uniform(0, 2 * np.pi)
    log_p = (np.log(base) + drift * t
             + amp * np.sin(2 * np.pi * idx.month / 12 + phase)
             + np.cumsum(rng.normal(0, 0.012, months)))
    return pd.DataFrame({"date": idx, "price": np.exp(log_p).round(2)})


def load_prices(crop: str) -> tuple[pd.DataFrame, str]:
    """Load at least 8 months of prices from either project CSV."""
    key = normalise_crop(crop)

    for path in (DATA_PATH, HISTORICAL_DATA_PATH):
        if not path.exists():
            continue

        try:
            df = pd.read_csv(path)
            df.columns = [column.strip().lower() for column in df.columns]

            # The existing crop dataset uses Commodity and Modal_Price.
            if "crop" not in df.columns and "commodity" in df.columns:
                df = df.rename(columns={"commodity": "crop"})
            if "price" not in df.columns and "modal_price" in df.columns:
                df = df.rename(columns={"modal_price": "price"})

            if not {"date", "crop", "price"}.issubset(df.columns):
                continue

            matching_crop = df["crop"].map(normalise_crop) == key
            prices = df.loc[matching_crop, ["date", "price"]].copy()
            prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
            prices["price"] = pd.to_numeric(prices["price"], errors="coerce")
            prices = prices.dropna()
            prices = prices[prices["price"] > 0]

            # The forecast needs at least 8 different months of price history.
            if not prices.empty and prices["date"].dt.to_period("M").nunique() >= 8:
                return prices.reset_index(drop=True), "real"

        except Exception:
            continue

    return _demo_series(crop), "demo"


# --------------------------------------------------------------------------- #
# Collecting real data (run daily to build history)
# --------------------------------------------------------------------------- #
# Verify this resource id on data.gov.in ("Current Daily Price of Various Commodities
# from Various Markets (Mandi)") - ids can change.
AGMARKNET_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"


def fetch_daily_snapshot(api_key: str, state: str = "Kerala", limit: int = 1000) -> int:
    """Download today's mandi prices for `state` and append to DATA_PATH. Returns rows added."""
    import requests

    url = f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE}"
    params = {"api-key": api_key, "format": "json", "limit": limit,
              "filters[state.keyword]": state}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    records = r.json().get("records", [])
    if not records:
        return 0

    new = pd.DataFrame(records)
    new = pd.DataFrame({
        "date": pd.to_datetime(new["arrival_date"], format="%d/%m/%Y", errors="coerce"),
        "crop": new["commodity"],
        "price": pd.to_numeric(new["modal_price"], errors="coerce"),
        "market": new.get("market"),
        "district": new.get("district"),
    }).dropna(subset=["date", "price"])

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DATA_PATH.exists():
        old = pd.read_csv(DATA_PATH, parse_dates=["date"])
        combined = pd.concat([old, new], ignore_index=True)
    else:
        combined = new
    before = len(combined)
    combined = combined.drop_duplicates(subset=["date", "crop", "market"], keep="last")
    combined.to_csv(DATA_PATH, index=False)
    return len(new)
