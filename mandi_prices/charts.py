"""
charts.py — Altair chart builders for the mandi price dashboard.

Altair ships with Streamlit, so this adds no new runtime dependency.
All charts are styled for the app's dark theme.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

ACCENT = "#00c853"
MUTED = "#9e9eb8"
GRID = "#2a2a4a"
CARD = "#1e1e36"

DISTRICT_COLORS = ["#00c853", "#69f0ae", "#ffd54f", "#4fc3f7", "#ff8a65", "#ba68c8", "#f06292"]

MA_COLORS = {7: "#ffd54f", 30: "#4fc3f7"}


def _style(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_view(stroke=None)
        .configure_axis(
            gridColor=GRID,
            labelColor=MUTED,
            titleColor=MUTED,
            domainColor=GRID,
            tickColor=GRID,
            labelFontSize=11,
        )
        .configure_legend(labelColor=MUTED, titleColor=MUTED, orient="top")
        .configure_title(color=MUTED)
    )


def empty_chart(message: str = "No data for the current filters") -> alt.Chart:
    frame = pd.DataFrame({"x": [0], "y": [0], "label": [message]})
    return _style(
        alt.Chart(frame)
        .mark_text(color=MUTED, fontSize=13)
        .encode(x=alt.X("x:Q", axis=None), y=alt.Y("y:Q", axis=None), text="label:N")
        .properties(height=240)
    )


def trend_chart(series: pd.DataFrame, height: int = 380) -> alt.Chart:
    """Price trend. Single district gets a min-max band; multiple get one line each."""
    if series is None or series.empty:
        return empty_chart()

    base = alt.Chart(series)
    districts = series["district"].nunique()

    if districts == 1:
        band = base.mark_area(color=ACCENT, opacity=0.16).encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("min_price:Q", title="₹ per quintal"),
            y2="max_price:Q",
            tooltip=[
                alt.Tooltip("date:T", format="%d %b %Y", title="Date"),
                alt.Tooltip("min_price:Q", format=",.0f", title="Min"),
                alt.Tooltip("max_price:Q", format=",.0f", title="Max"),
            ],
        )
        line = base.mark_line(color=ACCENT, strokeWidth=2.2).encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("modal_price:Q", title="₹ per quintal"),
            tooltip=[
                alt.Tooltip("date:T", format="%d %b %Y", title="Date"),
                alt.Tooltip("modal_price:Q", format=",.0f", title="Modal price"),
                alt.Tooltip("district:N", title="District"),
            ],
        )
        layers: list[alt.Chart] = [band, line]

        for window, color in MA_COLORS.items():
            column = f"ma_{window}"
            if column in series.columns:
                layers.append(
                    base.mark_line(color=color, strokeWidth=1.3, strokeDash=[5, 3]).encode(
                        x=alt.X("date:T", title=None),
                        y=alt.Y(f"{column}:Q"),
                        tooltip=[
                            alt.Tooltip("date:T", format="%d %b %Y", title="Date"),
                            alt.Tooltip(f"{column}:Q", format=",.0f", title=f"{window}-day avg"),
                        ],
                    )
                )
    else:
        line = base.mark_line(strokeWidth=2).encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("modal_price:Q", title="₹ per quintal"),
            color=alt.Color(
                "district:N",
                scale=alt.Scale(range=DISTRICT_COLORS),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                alt.Tooltip("date:T", format="%d %b %Y", title="Date"),
                alt.Tooltip("district:N", title="District"),
                alt.Tooltip("modal_price:Q", format=",.0f", title="Modal price"),
            ],
        )
        layers = [line]

    return _style(alt.layer(*layers).properties(height=height).interactive())


def district_bar_chart(compare: pd.DataFrame) -> alt.Chart:
    """Average modal price per district, ranked."""
    if compare is None or compare.empty:
        return empty_chart()

    height = max(180, 46 * len(compare))
    base = alt.Chart(compare)
    x_domain = [0, float(compare["avg_modal"].max()) * 1.14]

    bars = base.mark_bar(cornerRadius=4).encode(
        x=alt.X("avg_modal:Q", title="Average modal price (₹/quintal)", scale=alt.Scale(domain=x_domain)),
        y=alt.Y("district:N", sort="-x", title=None),
        color=alt.Color(
            "avg_modal:Q",
            scale=alt.Scale(range=["#0b5c2a", ACCENT]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("district:N", title="District"),
            alt.Tooltip("avg_modal:Q", format=",.0f", title="Avg modal"),
            alt.Tooltip("min_modal:Q", format=",.0f", title="Low"),
            alt.Tooltip("max_modal:Q", format=",.0f", title="High"),
            alt.Tooltip("premium_pct:Q", format="+.1f", title="Premium %"),
            alt.Tooltip("days:Q", title="Days of data"),
        ],
    )

    labels = base.mark_text(align="left", dx=5, color="#e0e0e0", fontSize=11).encode(
        x="avg_modal:Q",
        y=alt.Y("district:N", sort="-x"),
        text=alt.Text("avg_modal:Q", format=",.0f"),
    )

    return _style(alt.layer(bars, labels).properties(height=height))


def price_heatmap(df: pd.DataFrame, height: int = 260) -> alt.Chart:
    """Date x district matrix — makes reporting gaps obvious."""
    if df is None or df.empty:
        return empty_chart()

    return _style(
        alt.Chart(df)
        .mark_rect()
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("district:N", title=None),
            color=alt.Color(
                "modal_price:Q",
                scale=alt.Scale(range=["#1e1e36", "#0b5c2a", ACCENT]),
                title="₹/quintal",
            ),
            tooltip=[
                alt.Tooltip("date:T", format="%d %b %Y", title="Date"),
                alt.Tooltip("district:N", title="District"),
                alt.Tooltip("modal_price:Q", format=",.0f", title="Modal price"),
            ],
        )
        .properties(height=height)
    )
