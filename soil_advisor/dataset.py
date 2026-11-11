"""Dataset loading and synthetic generation for the soil advisor.

Priority:
1. ``data/crop_recommendation.csv`` if present (columns N, P, K, temperature,
   humidity, ph, rainfall, label).
2. Synthetic rows generated from the Kerala crop profiles in ``profiles.py``.

The synthetic path keeps the app runnable offline and makes the data source
visible in the model metadata and UI.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from soil_advisor.profiles import CROP_PROFILES, FEATURES

LABEL = "label"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "crop_recommendation.csv"

# Hard physical bounds used when adding noise to synthetic rows.
FEATURE_BOUNDS: dict[str, tuple[float, float]] = {
    "N": (0, 300),
    "P": (0, 300),
    "K": (0, 300),
    "temperature": (-10, 55),
    "humidity": (0, 100),
    "ph": (0, 14),
    "rainfall": (0, 1000),
}


def generate_synthetic_dataset(
    rows_per_crop: int = 200,
    seed: int = 42,
    noise_fraction: float = 0.05,
) -> pd.DataFrame:
    """Generate overlapping, plausible rows for every Kerala crop profile.

    A little noise around each range prevents a perfectly separable dataset,
    which would make the reported accuracy look artificial.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | str]] = []

    for crop, profile in CROP_PROFILES.items():
        for _ in range(rows_per_crop):
            row: dict[str, float | str] = {}
            for feature in FEATURES:
                low, high = profile[feature]
                value = rng.uniform(low, high)
                value += rng.normal(0, (high - low) * noise_fraction)
                bound_low, bound_high = FEATURE_BOUNDS[feature]
                row[feature] = float(np.clip(value, bound_low, bound_high))
            row[LABEL] = crop
            rows.append(row)

    return pd.DataFrame(rows)


def normalize_label(value: object) -> object:
    """Make CSV labels match the display-name and Malayalam-name maps.

    Missing values are passed through so ``dropna`` can remove them.
    """
    if pd.isna(value):
        return value
    return str(value).strip().lower().replace(" ", "_")


def load_dataset(csv_path: str | Path = CSV_PATH) -> tuple[pd.DataFrame, str]:
    """Return ``(dataframe, source_label)``.

    Raises ``ValueError`` when a CSV exists but does not have the expected
    columns or has no usable rows.
    """
    path = Path(csv_path)
    if path.exists():
        df = pd.read_csv(path)
        missing = [column for column in FEATURES + [LABEL] if column not in df.columns]
        if missing:
            raise ValueError(
                f"{path.name} is missing required columns: {', '.join(missing)}. "
                f"Expected: {', '.join(FEATURES + [LABEL])}."
            )
        df = df[FEATURES + [LABEL]].copy()
        df[LABEL] = df[LABEL].map(normalize_label)
        df = df.dropna().reset_index(drop=True)
        if df.empty:
            raise ValueError(f"{path.name} has no usable rows after dropping missing values.")
        return df, f"csv:{path.name}"

    return generate_synthetic_dataset(), "synthetic_kerala_profiles"
