import streamlit as st
import sys, os
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from theme import init_theme, inject_global_css, render_sidebar
from auth import require_auth
from mandi_prices.loader import (
    load_price_data,
    crop_windows,
    districts_for_crop,
    coverage_matrix,
    latest_data_date,
    validate_data,
)
from mandi_prices import analytics as A
from mandi_prices.charts import trend_chart, district_bar_chart, price_heatmap
from mandi_prices.formatting import inr, pct

st.set_page_config(
    page_title="Karsh.Ai | Mandi Prices",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_theme(); inject_global_css(); require_auth(); render_sidebar()

st.markdown("### Mandi Prices")
st.markdown(
    "Daily wholesale prices for Kerala crops. Compare markets, check the trend, "
    "and see where your produce fetches the most."
)

df = load_price_data()
if df.empty:
    st.error("The price dataset is empty or could not be read.")
    st.stop()

windows = crop_windows(df)
crops = list(windows)
default_crop = "Coconut" if "Coconut" in crops else crops[0]
today = date.today()
dataset_as_of = min(today, latest_data_date(df) or today)

# ── Filters ─────────────────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns([1.0, 1.6, 1.5, 1.0])

with f1:
    crop = st.selectbox("Crop", crops, index=crops.index(default_crop), key="mandi_crop")

window_start, window_end = windows[crop]
as_of = min(today, window_end)
available = districts_for_crop(df, crop)

with f2:
    districts = st.multiselect(
        "Districts",
        available,
        default=available,
        key=f"mandi_districts_{crop}",
    )

with f3:
    default_start = max(window_start, (as_of - timedelta(days=89)))
    picked = st.date_input(
        "Date range",
        value=(default_start, as_of),
        min_value=window_start,
        max_value=window_end,
        key=f"mandi_dates_{crop}",
    )

with f4:
    st.markdown("&nbsp;")
    include_future = False
    if window_end > today:
        include_future = st.toggle(
            "Include future",
            value=False,
            help="The dataset contains synthetic rows dated after today. They are hidden by default.",
        )

if isinstance(picked, (tuple, list)):
    start, end = picked[0], picked[-1]
else:
    start, end = picked, picked

if not districts:
    st.info("Select at least one district to see prices.")
    st.stop()

if include_future:
    st.warning(
        "Showing future-dated synthetic rows. These are placeholders, not real market data.",
        icon="⚠️",
    )

fdf = A.filter_prices(
    df,
    crop=crop,
    districts=districts,
    start=start,
    end=end,
    include_future=include_future,
    as_of=as_of,
)

if fdf.empty:
    st.info(
        f"No trading data for **{crop}** between {start:%d %b %Y} and {end:%d %b %Y}. "
        f"{crop} is reported from {window_start:%d %b %Y} to {window_end:%d %b %Y}."
    )
    st.stop()

# ── KPI row ─────────────────────────────────────────────────────────────────
snapshot = A.latest_snapshot(fdf, lookback_days=30, as_of=as_of)
stats = A.window_stats(fdf)
best = A.best_market(fdf)


def kpi_card(label: str, value: str, sub: str = "", tone: str = "flat") -> str:
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub kpi-{tone}">{sub}</div>'
        f"</div>"
    )


if snapshot["change"] is None:
    change_value, change_sub, change_tone = "—", "Not enough history in range", "flat"
else:
    change_tone = "up" if snapshot["change"] > 0 else "down" if snapshot["change"] < 0 else "flat"
    change_value = inr(snapshot["change"], signed=True)
    change_sub = f"{pct(snapshot['change_pct'])} over 30 days"

if best is None:
    best_value, best_sub = "—", "No market data"
elif best["markets_compared"] == 1:
    best_value = best["district"]
    best_sub = "Only one market reports this crop"
else:
    best_value = best["district"]
    best_sub = f"+{inr(best['avg_daily_premium'])}/qtl vs {best['cheapest_district']} on an average day"

k1, k2, k3, k4, k5 = st.columns(5)
k1.markdown(
    kpi_card(
        "CURRENT PRICE",
        inr(snapshot["price"]),
        f"on {snapshot['date']:%d %b %Y}" if snapshot["date"] else "no data",
    ),
    unsafe_allow_html=True,
)
k2.markdown(kpi_card("30-DAY CHANGE", change_value, change_sub, change_tone), unsafe_allow_html=True)
k3.markdown(
    kpi_card(
        "RANGE IN VIEW",
        f"{inr(stats['min'])} – {inr(stats['max'])}" if stats["count"] else "—",
        f"{stats['count']} observations",
    ),
    unsafe_allow_html=True,
)
k4.markdown(
    kpi_card(
        "VOLATILITY",
        pct(stats["cv"], signed=False) if stats["cv"] is not None else "—",
        f"{stats['volatility']} volatility",
    ),
    unsafe_allow_html=True,
)
k5.markdown(kpi_card("BEST DISTRICT TO SELL", best_value, best_sub), unsafe_allow_html=True)

st.markdown("")

# ── Tabs ────────────────────────────────────────────────────────────────────
tab_trend, tab_compare, tab_signal, tab_data = st.tabs(
    ["Trend", "Compare Markets", "Sell Signal", "Data & Coverage"]
)

# Trend ----------------------------------------------------------------------
with tab_trend:
    series = A.price_series(fdf)
    st.altair_chart(trend_chart(series), width="stretch")

    if series["district"].nunique() == 1:
        st.caption(
            "Shaded band = that day's min–max range. Dashed lines = 7-day and 30-day averages."
        )
    else:
        st.caption(
            "One line per district. Select a single district to see its min–max band and averages."
        )

    monthly = A.monthly_summary(fdf)
    if not monthly.empty:
        with st.expander("Month-by-month summary"):
            display = monthly.rename(
                columns={
                    "period": "Month",
                    "avg_modal": "Avg modal (₹)",
                    "min_price": "Low (₹)",
                    "max_price": "High (₹)",
                    "observations": "Observations",
                }
            )
            st.dataframe(
                display.style.format(
                    {"Avg modal (₹)": "{:,.0f}", "Low (₹)": "{:,.0f}", "High (₹)": "{:,.0f}"}
                ),
                width="stretch",
                hide_index=True,
            )

# Compare --------------------------------------------------------------------
with tab_compare:
    compare = A.district_comparison(fdf)

    if len(compare) == 1:
        st.info(
            f"Only **{compare.iloc[0]['district']}** reports prices for {crop}, "
            "so there is nothing to compare."
        )

    st.altair_chart(district_bar_chart(compare), width="stretch")

    display = compare.rename(
        columns={
            "rank": "#",
            "district": "District",
            "avg_modal": "Avg modal (₹)",
            "min_modal": "Low (₹)",
            "max_modal": "High (₹)",
            "avg_daily_premium": "Avg daily premium (₹)",
            "avg_spread": "Avg day spread (₹)",
            "days": "Days",
            "premium_pct": "Premium %",
        }
    )
    st.dataframe(
        display.style.format(
            {
                "Avg modal (₹)": "{:,.0f}",
                "Low (₹)": "{:,.0f}",
                "High (₹)": "{:,.0f}",
                "Avg daily premium (₹)": "{:,.0f}",
                "Avg day spread (₹)": "{:,.0f}",
                "Premium %": "{:+.2f}",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "Premium is measured against the cheapest district in view. Average daily premium "
        "is what this district fetched above that day's cheapest market; day spread is the "
        "gap between the day's minimum and maximum price."
    )

    st.markdown("#### Reporting coverage")
    st.altair_chart(price_heatmap(fdf), width="stretch")
    st.caption("Blank cells mean no reported price for that district on that date.")

# Sell signal ----------------------------------------------------------------
with tab_signal:
    signal = A.sell_signal(fdf, lookback_days=90, as_of=as_of)

    if signal is None:
        st.info("Not enough data to build a signal for this selection.")
    elif signal["percentile"] is None:
        st.info(signal["rationale"])
    else:
        st.markdown(f"### {signal['label']}")
        st.progress(min(max(signal["percentile"] / 100, 0.0), 1.0))
        st.markdown(signal["rationale"])

        s1, s2, s3 = st.columns(3)
        s1.metric("90-day low", inr(signal["window_min"]))
        s2.metric("Current", inr(signal["current"]))
        s3.metric("90-day high", inr(signal["window_max"]))

    st.caption(
        "This is a heuristic based on where today's price sits inside its recent range. "
        "It is not a forecast and not financial advice — storage costs, quality and "
        "local demand matter just as much."
    )

# Data -----------------------------------------------------------------------
with tab_data:
    st.markdown("#### Cross-crop snapshot")
    table = A.crop_price_table(df, as_of=dataset_as_of)
    if not table.empty:
        display = table.rename(
            columns={
                "crop": "Crop",
                "latest_date": "Latest date",
                "modal_price": "Modal (₹)",
                "change_30d": "30d change (₹)",
                "change_30d_pct": "30d change %",
                "districts": "Districts",
                "observations": "Rows",
            }
        )
        st.dataframe(
            display.style.format(
                {
                    "Modal (₹)": "{:,.0f}",
                    "30d change (₹)": "{:+,.0f}",
                    "30d change %": "{:+.1f}",
                },
                na_rep="—",
            ),
            width="stretch",
            hide_index=True,
        )
        st.caption("Each crop is measured against its own latest available date.")
    st.markdown("#### Selected rows")
    st.dataframe(
        fdf[
            ["date", "district", "market", "crop", "variety", "min_price", "max_price", "modal_price"]
        ].rename(
            columns={
                "date": "Date",
                "district": "District",
                "market": "Market",
                "crop": "Crop",
                "variety": "Variety",
                "min_price": "Min (₹)",
                "max_price": "Max (₹)",
                "modal_price": "Modal (₹)",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        "Download selected rows as CSV",
        data=fdf.to_csv(index=False).encode("utf-8"),
        file_name=f"karsh_mandi_{crop.lower().replace(' ', '_')}_{start}_{end}.csv",
        mime="text/csv",
    )

    with st.expander("Dataset health & coverage"):
        st.json(validate_data(df, as_of=dataset_as_of))
        matrix = coverage_matrix(df)
        if not matrix.empty:
            st.markdown("**Rows per crop and district**")
            st.dataframe(matrix.reset_index(), width="stretch", hide_index=True)

    st.caption(
        "Source: Karsh.Ai bundled dataset. The current series is synthetic and covers "
        "a limited window per crop — treat it as a UI preview, not live market data."
    )

st.markdown('<div class="footer-text">Karsh.Ai · Mandi prices</div>', unsafe_allow_html=True)
