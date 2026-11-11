"""Train, persist and use the soil-based crop recommendation model.

The model is a RandomForestClassifier over seven soil/climate features. It is
trained on first use (or via ``python -m soil_advisor.train``) and stored under
``models/`` together with a JSON metadata file. The metadata is what the UI
uses to show accuracy, data source and training ranges honestly.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

from soil_advisor.dataset import FEATURES, LABEL, load_dataset, normalize_label
from soil_advisor.profiles import CROP_DISPLAY_NAMES, CROP_MALAYALAM_NAMES

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_FILENAME = "soil_crop_model.pkl"
META_FILENAME = "soil_crop_model_meta.json"
MODEL_VERSION = "1.0.0"
RANDOM_STATE = 42

_MODEL: RandomForestClassifier | None = None
_META: dict | None = None


def _top_k_accuracy(model: RandomForestClassifier, X_test: pd.DataFrame, y_test: pd.Series, k: int = 3) -> float:
    probabilities = model.predict_proba(X_test)
    classes = np.asarray(model.classes_)
    top_indices = np.argsort(probabilities, axis=1)[:, -k:]
    hits = [
        y_test.iloc[row] in set(classes[top_indices[row]])
        for row in range(len(y_test))
    ]
    return float(np.mean(hits)) if hits else 0.0


def train_model(
    dataset: pd.DataFrame | None = None,
    model_dir: str | Path = MODEL_DIR,
    n_estimators: int = 200,
    test_size: float = 0.2,
    random_state: int = RANDOM_STATE,
) -> tuple[RandomForestClassifier, dict]:
    """Train and save the model. Returns ``(model, metadata)``."""
    if dataset is None:
        dataset, source = load_dataset()
    else:
        source = "provided_dataframe"

    missing = [column for column in FEATURES + [LABEL] if column not in dataset.columns]
    if missing:
        raise ValueError(f"Training data is missing columns: {', '.join(missing)}.")

    data = dataset[FEATURES + [LABEL]].copy()
    data[LABEL] = data[LABEL].map(normalize_label)
    data = data.dropna().reset_index(drop=True)
    if data.empty:
        raise ValueError("Training data has no usable rows.")

    X = data[FEATURES].astype(float)
    y = data[LABEL]

    # Stratify only when every class has enough rows for both sides of the split.
    class_counts = y.value_counts()
    can_stratify = (
        class_counts.min() >= 2
        and len(y) * test_size >= y.nunique()
    )
    stratify = y if can_stratify else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "macro_f1": round(float(f1_score(y_test, predictions, average="macro", zero_division=0)), 4),
        "top3_accuracy": round(_top_k_accuracy(model, X_test, y_test, k=min(3, len(model.classes_))), 4),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
    }

    training_ranges = {
        feature: [
            round(float(X_train[feature].min()), 3),
            round(float(X_train[feature].max()), 3),
        ]
        for feature in FEATURES
    }
    feature_importance = dict(
        sorted(
            (
                (feature, round(float(value), 4))
                for feature, value in zip(FEATURES, model.feature_importances_)
            ),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_source": source,
        "dataset_rows": int(len(data)),
        "classes": [str(label) for label in model.classes_],
        "features": FEATURES,
        "metrics": metrics,
        "training_ranges": training_ranges,
        "feature_importance": feature_importance,
        "train_test_split": (
            f"{int(round((1 - test_size) * 100))}/{int(round(test_size * 100))} stratified"
            if stratify is not None
            else f"{int(round((1 - test_size) * 100))}/{int(round(test_size * 100))} random"
        ),
        "random_state": random_state,
        "n_estimators": n_estimators,
        "sklearn_version": sklearn.__version__,
        "notes": (
            "Demo model. Replace data/crop_recommendation.csv with measured soil "
            "data before using this for real agronomic decisions."
        ),
    }

    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / MODEL_FILENAME)
    (model_dir / META_FILENAME).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return model, metadata


def load_model(model_dir: str | Path = MODEL_DIR) -> RandomForestClassifier:
    path = Path(model_dir) / MODEL_FILENAME
    if not path.exists():
        raise FileNotFoundError(f"No trained soil model at {path}.")
    return joblib.load(path)


def get_metadata(model_dir: str | Path = MODEL_DIR) -> dict | None:
    path = Path(model_dir) / META_FILENAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def ensure_model(
    model_dir: str | Path = MODEL_DIR,
    force: bool = False,
) -> tuple[RandomForestClassifier, dict]:
    """Load the cached model, or train it if no artefacts exist yet."""
    global _MODEL, _META

    directory = Path(model_dir)
    is_default = directory.resolve() == MODEL_DIR.resolve()

    if not force and is_default and _MODEL is not None and _META is not None:
        return _MODEL, _META

    model_path = directory / MODEL_FILENAME
    meta_path = directory / META_FILENAME
    if not force and model_path.exists() and meta_path.exists():
        model = joblib.load(model_path)
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        model, metadata = train_model(model_dir=directory)

    if is_default:
        _MODEL, _META = model, metadata
    return model, metadata


def predict_crops(
    features: dict[str, float],
    top_k: int = 3,
    model: RandomForestClassifier | None = None,
    metadata: dict | None = None,
) -> dict:
    """Return the top-k crops with probabilities and display names."""
    missing = [feature for feature in FEATURES if feature not in features]
    if missing:
        raise ValueError(f"Missing model features: {', '.join(missing)}.")

    if model is None or metadata is None:
        model, metadata = ensure_model()

    row = pd.DataFrame(
        [[float(features[feature]) for feature in FEATURES]],
        columns=FEATURES,
    )
    probabilities = model.predict_proba(row)[0]
    classes = np.asarray(model.classes_)
    order = np.argsort(probabilities)[::-1][: max(1, int(top_k))]

    predictions = []
    for index in order:
        crop = str(classes[index])
        predictions.append(
            {
                "crop": crop,
                "display_name": CROP_DISPLAY_NAMES.get(crop, crop.replace("_", " ").title()),
                "malayalam_name": CROP_MALAYALAM_NAMES.get(crop, ""),
                "probability": round(float(probabilities[index]) * 100, 2),
            }
        )

    return {
        "predictions": predictions,
        "model_version": metadata.get("model_version"),
        "dataset_source": metadata.get("dataset_source"),
        "top_feature_importance": metadata.get("feature_importance", {}),
    }
