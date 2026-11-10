"""Tests for the mandi price data layer and analytics."""

from datetime import date

import pandas as pd
import pytest

from mandi_prices import analytics as A
from mandi_prices.charts import district_bar_chart, price_heatmap, trend_chart
from mandi_prices.formatting import inr, pct
from mandi_prices.loader import (
    DEFAULT_DATA_PATH,
    _read_dataframe,
    coverage_matrix,
    crop_windows,
    districts_for_crop,
    validate_data,
)

AS_OF = date(2026, 11, 10)


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return _read_dataframe(DEFAULT_DATA_PATH)


# ── Data integrity ──────────────────────────────────────────────────────────


def test_dataset_shape_and_integrity(df):
    report = validate_data(df, as_of=AS_OF)

    assert report["rows"] == 2003
    assert report["crops"] == 7
    assert report["districts"] == 11
    assert report["markets"] == 11
    assert report["blank_cells"] == 0
    assert report["duplicate_rows"] == 0
    assert report["invalid_price_ranges"] == 0
    assert report["status"] == "ok"
    assert report["max_gap_days"] == 92  # Coconut is missing Apr-Jun


def test_crop_windows_are_exact(df):
    windows = crop_windows(df)

    assert windows["Tapioca"] == (date(2026, 1, 1), date(2026, 3, 31))
    assert windows["Coconut"] == (date(2026, 1, 1), date(2026, 9, 30))
    assert windows["Paddy"] == (date(2026, 4, 1), date(2026, 6, 30))
    assert windows["Rubber"] == (date(2026, 4, 1), date(2026, 6, 30))
    assert windows["Banana"] == (date(2026, 7, 1), date(2026, 9, 30))
    assert windows["Black Pepper"] == (date(2026, 10, 1), date(2026, 12, 31))
    assert windows["Cardamom"] == (date(2026, 10, 1), date(2026, 12, 31))


def test_coverage_matrix_shape(df):
    matrix = coverage_matrix(df)

    assert matrix.shape == (7, 11)
    assert int(matrix.loc["Cardamom"].sum()) == 92
    assert int(matrix.loc["Coconut", "Ernakulam"]) == 182
    assert int(matrix.loc["Cardamom", "Kollam"]) == 0


def test_districts_for_crop(df):
    assert districts_for_crop(df, "Coconut") == [
        "Alappuzha",
        "Ernakulam",
        "Kozhikode",
        "Palakkad",
    ]
    assert districts_for_crop(df, "Cardamom") == ["Idukki"]


# ── Filtering and date safety ───────────────────────────────────────────────


def test_filter_excludes_future_rows(df):
    filtered = A.filter_prices(df, as_of=AS_OF)

    assert not filtered.empty
    assert filtered["date"].max().date() <= AS_OF
    assert len(filtered) == 2003 - 153


def test_filter_can_include_future_rows(df):
    filtered = A.filter_prices(df, as_of=AS_OF, include_future=True)

    assert len(filtered) == 2003
    assert filtered["date"].max().date() > AS_OF


def test_empty_filter_returns_empty_frame(df):
    empty = A.filter_prices(
        df, crop="Coconut", start=date(2026, 4, 1), end=date(2026, 6, 30)
    )

    assert empty.empty
    # Downstream analytics must not explode on an empty frame.
    assert A.latest_snapshot(empty)["price"] is None
    assert A.window_stats(empty)["count"] == 0
    assert A.district_comparison(empty).empty
    assert A.best_market(empty) is None
    assert A.sell_signal(empty) is None
    assert A.price_series(empty).empty
    assert A.crop_price_table(empty).empty


# ── Analytics ───────────────────────────────────────────────────────────────


def test_latest_snapshot_respects_as_of(df):
    pepper = A.filter_prices(df, crop="Black Pepper", include_future=True)
    snapshot = A.latest_snapshot(pepper, lookback_days=30, as_of=AS_OF)

    assert snapshot["date"] <= AS_OF
    assert snapshot["price"] > 0
    assert snapshot["prev_date"] <= snapshot["date"]


def test_latest_snapshot_uses_nearest_available_date(df):
    """Coconut jumps Apr-Jun, so a calendar-exact lookup would find nothing."""
    coconut = A.filter_prices(df, crop="Coconut", as_of=AS_OF)
    snapshot = A.latest_snapshot(coconut, lookback_days=30, as_of=AS_OF)

    assert snapshot["date"] == date(2026, 9, 30)
    assert snapshot["prev_date"] is not None
    assert snapshot["change"] is not None


def test_window_stats(df):
    tapioca = A.filter_prices(df, crop="Tapioca", as_of=AS_OF)
    stats = A.window_stats(tapioca)

    assert stats["count"] == 360
    assert stats["min"] <= stats["median"] <= stats["max"]
    assert stats["cv"] is not None and stats["cv"] > 0
    assert stats["volatility"] in {"Low", "Moderate", "High"}


def test_district_comparison_and_best_market(df):
    coconut = A.filter_prices(df, crop="Coconut", as_of=AS_OF)
    compare = A.district_comparison(coconut)
    best = A.best_market(coconut)

    assert len(compare) == 4
    assert compare.iloc[0]["avg_modal"] >= compare.iloc[-1]["avg_modal"]
    assert compare["premium_pct"].min() == pytest.approx(0.0)

    assert best is not None
    assert best["district"] in districts_for_crop(df, "Coconut")
    assert best["premium_pct"] >= 0
    assert best["markets_compared"] == 4
    assert best["spread"] >= 0


def test_single_market_comparison(df):
    cardamom = A.filter_prices(df, crop="Cardamom", as_of=AS_OF)
    best = A.best_market(cardamom)

    assert best is not None
    assert best["district"] == "Idukki"
    assert best["markets_compared"] == 1
    assert best["premium_pct"] == pytest.approx(0.0)


def test_sell_signal_bounds(df):
    for crop in crop_windows(df):
        subset = A.filter_prices(df, crop=crop, as_of=AS_OF)
        signal = A.sell_signal(subset, as_of=AS_OF)
        if signal is not None and signal["percentile"] is not None:
            assert 0.0 <= signal["percentile"] <= 100.0
            assert signal["window_min"] <= signal["current"] <= signal["window_max"]


def test_price_series_rolling_is_per_district(df):
    rubber = A.filter_prices(df, crop="Rubber", as_of=AS_OF)
    series = A.price_series(rubber)

    assert set(series["district"]) == {"Idukki", "Kottayam", "Pathanamthitta"}
    assert series["ma_7"].notna().all()
    # First observation of each district equals its own price (min_periods=1).
    firsts = series.groupby("district").first()
    assert (firsts["ma_7"] == firsts["modal_price"]).all()


def test_crop_price_table(df):
    table = A.crop_price_table(df, as_of=AS_OF)

    assert len(table) == 7
    assert table["modal_price"].gt(0).all()
    assert set(table["crop"]) == set(crop_windows(df))


# ── Charts ──────────────────────────────────────────────────────────────────


def test_charts_build_valid_vega_specs(df):
    """to_dict() validates the encoding, so a malformed chart raises here."""
    coconut = A.filter_prices(df, crop="Coconut", as_of=AS_OF)
    series = A.price_series(coconut)
    single = series[series["district"] == "Ernakulam"]

    specs = [
        trend_chart(series).to_dict(),
        trend_chart(single).to_dict(),
        district_bar_chart(A.district_comparison(coconut)).to_dict(),
        price_heatmap(coconut).to_dict(),
        trend_chart(pd.DataFrame()).to_dict(),
    ]

    for spec in specs:
        assert "layer" in spec or "mark" in spec


# ── Formatting ──────────────────────────────────────────────────────────────


def test_indian_rupee_formatting():
    assert inr(3500) == "₹3,500"
    assert inr(194994) == "₹1,94,994"
    assert inr(12345678) == "₹1,23,45,678"
    assert inr(None) == "—"
    assert inr(-250, signed=True) == "−₹250"
    assert pct(4.25) == "+4.2%"
    assert pct(None) == "—"
