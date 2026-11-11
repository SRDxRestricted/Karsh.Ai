"""Retrain the soil advisor from the command line.

Usage:
    python -m soil_advisor.train
"""

from __future__ import annotations

import json

from soil_advisor.model import MODEL_DIR, train_model


def main() -> None:
    model, metadata = train_model()
    print(f"Trained on {metadata['dataset_rows']} rows from {metadata['dataset_source']}.")
    print(f"Classes: {', '.join(metadata['classes'])}")
    print(json.dumps(metadata["metrics"], indent=2))
    print(f"Saved model to {MODEL_DIR}.")


if __name__ == "__main__":
    main()
