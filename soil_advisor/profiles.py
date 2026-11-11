"""Agronomic envelopes for the demo Kerala crop-recommendation model.

Each range is an approximate, deliberately broad envelope for a crop grown in
Kerala. The values are for a demo model, not a substitute for a soil test or
for district-level agronomic advice. Replace ``data/crop_recommendation.csv``
with measured data to train on real observations.
"""

from __future__ import annotations

# Feature order is shared by the dataset, model and UI.
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

# N, P and K are plant-available nutrients in mg/kg; temperature is °C,
# humidity is %, rainfall is mm (seasonal total).
CROP_PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    "rice": {
        "N": (60, 110), "P": (30, 60), "K": (30, 55),
        "temperature": (22, 32), "humidity": (75, 92), "ph": (5.5, 7.0), "rainfall": (150, 320),
    },
    "coconut": {
        "N": (40, 110), "P": (20, 55), "K": (60, 130),
        "temperature": (24, 33), "humidity": (70, 90), "ph": (5.0, 7.5), "rainfall": (150, 320),
    },
    "banana": {
        "N": (80, 140), "P": (55, 105), "K": (50, 90),
        "temperature": (24, 32), "humidity": (70, 90), "ph": (5.5, 7.0), "rainfall": (100, 260),
    },
    "rubber": {
        "N": (35, 95), "P": (20, 50), "K": (30, 75),
        "temperature": (24, 33), "humidity": (75, 92), "ph": (4.5, 6.5), "rainfall": (200, 360),
    },
    "black_pepper": {
        "N": (50, 115), "P": (30, 70), "K": (50, 105),
        "temperature": (22, 30), "humidity": (75, 92), "ph": (5.0, 6.5), "rainfall": (200, 360),
    },
    "cardamom": {
        "N": (40, 95), "P": (20, 50), "K": (40, 85),
        "temperature": (18, 27), "humidity": (80, 96), "ph": (5.0, 6.5), "rainfall": (220, 400),
    },
    "tapioca": {
        "N": (40, 95), "P": (20, 50), "K": (40, 85),
        "temperature": (24, 33), "humidity": (65, 85), "ph": (5.0, 6.5), "rainfall": (100, 260),
    },
    "coffee": {
        "N": (60, 115), "P": (20, 50), "K": (40, 85),
        "temperature": (20, 28), "humidity": (70, 90), "ph": (5.5, 7.0), "rainfall": (150, 320),
    },
    "tea": {
        "N": (60, 125), "P": (20, 50), "K": (40, 85),
        "temperature": (18, 27), "humidity": (80, 96), "ph": (4.5, 6.0), "rainfall": (220, 400),
    },
    "ginger": {
        "N": (50, 105), "P": (30, 65), "K": (50, 105),
        "temperature": (22, 31), "humidity": (70, 90), "ph": (5.5, 7.0), "rainfall": (150, 320),
    },
    "turmeric": {
        "N": (50, 105), "P": (30, 65), "K": (50, 105),
        "temperature": (22, 32), "humidity": (70, 90), "ph": (5.5, 7.5), "rainfall": (150, 320),
    },
    "tomato": {
        "N": (60, 125), "P": (40, 85), "K": (50, 105),
        "temperature": (20, 30), "humidity": (60, 85), "ph": (5.5, 7.0), "rainfall": (80, 220),
    },
}

CROP_DISPLAY_NAMES: dict[str, str] = {
    "rice": "Paddy (Rice)",
    "coconut": "Coconut",
    "banana": "Banana",
    "rubber": "Rubber",
    "black_pepper": "Black Pepper",
    "cardamom": "Cardamom",
    "tapioca": "Tapioca",
    "coffee": "Coffee",
    "tea": "Tea",
    "ginger": "Ginger",
    "turmeric": "Turmeric",
    "tomato": "Tomato",
}

CROP_MALAYALAM_NAMES: dict[str, str] = {
    "rice": "നെല്ല്",
    "coconut": "തെങ്ങ്",
    "banana": "വാഴ",
    "rubber": "റബ്ബർ",
    "black_pepper": "കുരുമുളക്",
    "cardamom": "ഏലം",
    "tapioca": "കപ്പ",
    "coffee": "കാപ്പി",
    "tea": "തേയില",
    "ginger": "ഇഞ്ചി",
    "turmeric": "മഞ്ഞൾ",
    "tomato": "തക്കാളി",
}
