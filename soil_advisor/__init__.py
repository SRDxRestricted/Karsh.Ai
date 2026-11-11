"""Soil-based crop recommendation for Karsh.Ai.

The package trains a small RandomForest on soil and climate features and
returns the most likely crops with confidence scores. It ships with
synthetic Kerala crop profiles so the app works out of the box; drop a real
dataset at ``data/crop_recommendation.csv`` to train on measured data.
"""

__version__ = "1.0.0"
