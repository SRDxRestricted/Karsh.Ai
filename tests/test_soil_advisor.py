from __future__ import annotations

import pytest

from soil_advisor.dataset import FEATURES, LABEL, generate_synthetic_dataset, load_dataset
from soil_advisor.model import get_metadata, predict_crops, train_model
from soil_advisor.validation import (
    MG_PER_KG_TO_KG_PER_HA,
    SoilInput,
    outside_training_range,
)


def _sample_input(**overrides) -> SoilInput:
    values = {
        "N": 80.0,
        "P": 45.0,
        "K": 50.0,
        "temperature": 27.0,
        "humidity": 80.0,
        "ph": 6.5,
        "rainfall": 200.0,
    }
    values.update(overrides)
    return SoilInput(**values)


def test_synthetic_dataset_has_expected_shape_and_classes():
    dataset = generate_synthetic_dataset(rows_per_crop=10, seed=1)

    assert list(dataset.columns) == FEATURES + [LABEL]
    assert len(dataset) == 120
    assert dataset[LABEL].nunique() == 12
    assert dataset[FEATURES].notna().all().all()


def test_training_writes_artifacts_and_metadata(tmp_path):
    dataset = generate_synthetic_dataset(rows_per_crop=30, seed=123)

    model, metadata = train_model(
        dataset=dataset,
        model_dir=tmp_path,
        n_estimators=40,
        random_state=7,
    )

    assert (tmp_path / "soil_crop_model.pkl").exists()
    assert (tmp_path / "soil_crop_model_meta.json").exists()
    assert metadata["dataset_source"] == "provided_dataframe"
    assert metadata["dataset_rows"] == len(dataset)
    assert 0.0 <= metadata["metrics"]["accuracy"] <= 1.0
    assert metadata["metrics"]["top3_accuracy"] >= metadata["metrics"]["accuracy"]
    assert set(metadata["training_ranges"]) == set(FEATURES)
    assert get_metadata(tmp_path)["model_version"] == metadata["model_version"]

    predictions = model.predict(dataset[FEATURES].head(1))
    assert len(predictions) == 1


def test_predict_returns_sorted_top_k(tmp_path):
    dataset = generate_synthetic_dataset(rows_per_crop=30, seed=321)
    model, metadata = train_model(
        dataset=dataset,
        model_dir=tmp_path,
        n_estimators=40,
    )
    features = dataset[FEATURES].mean().to_dict()

    result = predict_crops(features, top_k=3, model=model, metadata=metadata)

    assert len(result["predictions"]) == 3
    probabilities = [item["probability"] for item in result["predictions"]]
    assert probabilities == sorted(probabilities, reverse=True)
    assert sum(probabilities) <= 100.01
    assert all(item["display_name"] for item in result["predictions"])


def test_npk_unit_conversion_is_consistent():
    mg_reading = _sample_input()
    kg_reading = _sample_input(
        N=80.0 * MG_PER_KG_TO_KG_PER_HA,
        P=45.0 * MG_PER_KG_TO_KG_PER_HA,
        K=50.0 * MG_PER_KG_TO_KG_PER_HA,
        npk_unit="kg/ha",
    )

    mg_features = mg_reading.to_features()
    kg_features = kg_reading.to_features()
    for feature in ("N", "P", "K"):
        assert kg_features[feature] == pytest.approx(mg_features[feature], rel=1e-6)


def test_validation_rejects_out_of_range_values():
    with pytest.raises(ValueError, match="pH"):
        _sample_input(ph=15.0).validate()

    with pytest.raises(ValueError, match="Nitrogen"):
        _sample_input(N=-1.0).validate()


def test_outside_training_range_flags_unusual_inputs():
    warnings = outside_training_range({"N": 999.0}, {"N": [0.0, 300.0]})

    assert len(warnings) == 1
    assert "Nitrogen" in warnings[0]
    assert outside_training_range({"N": 100.0}, {"N": [0.0, 300.0]}) == []


def test_load_dataset_reads_csv_and_normalizes_labels(tmp_path):
    csv_path = tmp_path / "crop_recommendation.csv"
    data = generate_synthetic_dataset(rows_per_crop=2, seed=5)
    data[LABEL] = data[LABEL].str.title().str.replace("_", " ", regex=False)
    data.to_csv(csv_path, index=False)

    dataset, source = load_dataset(csv_path)

    assert source == "csv:crop_recommendation.csv"
    assert len(dataset) == 24
    assert list(dataset.columns) == FEATURES + [LABEL]
    assert "black_pepper" in set(dataset[LABEL])


def test_storage_round_trip(tmp_path, monkeypatch):
    import soil_advisor.storage as storage

    monkeypatch.setattr(storage, "DATA_FILE", tmp_path / "soil_readings.jsonl")
    storage.save_reading(
        "test-user",
        "Ernakulam",
        "Loamy",
        {"N": 80.0},
        {"predictions": [{"display_name": "Coconut", "probability": 42.0}]},
        "1.0.0",
    )

    records = storage.load_recent_readings("test-user")

    assert len(records) == 1
    assert records[0]["predictions"][0]["display_name"] == "Coconut"
    assert storage.load_recent_readings("another-user") == []
