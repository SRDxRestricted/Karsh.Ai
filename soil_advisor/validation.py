"""Input validation and unit conversion for the soil advisor."""

from __future__ import annotations

import math
from dataclasses import dataclass

# 1 mg/kg in a 0-15 cm layer with bulk density 1.5 g/cm3 is about 2.24 kg/ha.
MG_PER_KG_TO_KG_PER_HA = 2.24
NPK_UNITS = ("mg/kg", "kg/ha")

FEATURE_LABELS: dict[str, str] = {
    "N": "Nitrogen (N)",
    "P": "Phosphorus (P)",
    "K": "Potassium (K)",
    "temperature": "Temperature",
    "humidity": "Humidity",
    "ph": "pH",
    "rainfall": "Rainfall",
}

FEATURE_LIMITS: dict[str, tuple[float, float]] = {
    "N": (0, 300),
    "P": (0, 300),
    "K": (0, 300),
    "temperature": (-10, 55),
    "humidity": (0, 100),
    "ph": (0, 14),
    "rainfall": (0, 1000),
}


@dataclass(frozen=True)
class SoilInput:
    """One soil reading, in the units shown to the farmer."""

    N: float
    P: float
    K: float
    temperature: float
    humidity: float
    ph: float
    rainfall: float
    district: str = ""
    soil_type: str = ""
    land_area_ha: float | None = None
    npk_unit: str = "mg/kg"

    def to_features(self) -> dict[str, float]:
        """Convert the reading to the model's canonical units (mg/kg, °C, %, mm)."""
        if self.npk_unit not in NPK_UNITS:
            raise ValueError(f"Unsupported NPK unit: {self.npk_unit}. Use {', '.join(NPK_UNITS)}.")

        factor = 1.0 if self.npk_unit == "mg/kg" else 1.0 / MG_PER_KG_TO_KG_PER_HA
        return {
            "N": float(self.N) * factor,
            "P": float(self.P) * factor,
            "K": float(self.K) * factor,
            "temperature": float(self.temperature),
            "humidity": float(self.humidity),
            "ph": float(self.ph),
            "rainfall": float(self.rainfall),
        }

    def validate(self) -> None:
        """Raise ``ValueError`` with a farmer-readable message on bad input."""
        if self.npk_unit not in NPK_UNITS:
            raise ValueError(f"Unsupported NPK unit: {self.npk_unit}. Use {', '.join(NPK_UNITS)}.")

        features = self.to_features()
        for name, (low, high) in FEATURE_LIMITS.items():
            value = features[name]
            if not math.isfinite(value):
                raise ValueError(f"{FEATURE_LABELS[name]} must be a finite number.")
            if not low <= value <= high:
                unit = "mg/kg" if name in {"N", "P", "K"} else ""
                suffix = f" {unit}" if unit else ""
                raise ValueError(
                    f"{FEATURE_LABELS[name]} must be between {low:g} and {high:g}{suffix}."
                )

        if self.land_area_ha is not None and self.land_area_ha <= 0:
            raise ValueError("Land area must be greater than zero when provided.")


def outside_training_range(
    features: dict[str, float],
    training_ranges: dict[str, list[float]],
) -> list[str]:
    """Return readable warnings for inputs outside the model's training range."""
    warnings: list[str] = []
    for name, bounds in training_ranges.items():
        if name not in features or len(bounds) != 2:
            continue
        low, high = float(bounds[0]), float(bounds[1])
        value = features[name]
        if value < low or value > high:
            warnings.append(
                f"{FEATURE_LABELS.get(name, name)} ({value:g}) is outside the training "
                f"range ({low:g}-{high:g}); the prediction may be less reliable."
            )
    return warnings
