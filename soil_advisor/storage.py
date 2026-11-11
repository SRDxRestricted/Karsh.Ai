"""Lightweight history for soil recommendations.

Readings are appended to ``data/soil_readings.jsonl``. This is deliberately
simple: it gives the dashboard a history without introducing a database
dependency, and the file is gitignored.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "soil_readings.jsonl"


def save_reading(
    username: str,
    district: str,
    soil_type: str,
    features: dict[str, float],
    result: dict,
    model_version: str | None,
) -> dict:
    """Append one reading and return the stored record."""
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "username": username,
        "district": district,
        "soil_type": soil_type,
        "features": features,
        "predictions": result.get("predictions", []),
        "model_version": model_version,
        "dataset_source": result.get("dataset_source"),
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_recent_readings(username: str, limit: int = 5) -> list[dict]:
    """Return this user's most recent readings, newest first."""
    if not DATA_FILE.exists():
        return []

    try:
        lines = DATA_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    readings: list[dict] = []
    for line in reversed(lines):
        if len(readings) >= limit:
            break
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("username") == username:
            readings.append(record)
    return readings
