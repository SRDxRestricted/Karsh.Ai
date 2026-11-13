from datetime import date, timedelta
import altair as alt
import pandas as pd
import streamlit as st

# Approximate, editable harvest-duration defaults in days.
DEFAULT_GROWTH_DAYS = {
    "rice": 125,
    "paddy": 125,
    "banana": 317,  # approximate average for Nendran types
    "tapioca": 255,
    "ginger": 253,
    "turmeric": 258,
}

from price_forecaster import (
    explain_forecast, forecast_price_trend, get_supported_crops,
    InsufficientDataError, load_prices,
)

st.set_page_config(page_title="Price Trend Estimate", layout="wide")
st.title("Market Price Trend Estimate")
st.caption("Uses past market prices to estimate whether a crop's price may rise or fall.")
st.warning("⚠️ This is an ESTIMATE from past prices only. It is not a guarantee or financial advice.")
st.subheader("Estimate harvest date")

# --- Define helper functions first ---
@st.cache_data(ttl=3600, show_spinner=False)
def _crops():
    return get_supported_crops()

@st.cache_data(ttl=3600, show_spinner=False)
def _load(crop_name):
    return load_prices(crop_name)

# --- Layout Inputs ---
col1, col2 = st.columns([2, 1])
crop = col1.selectbox("Select Crop", _crops())
lang_label = col2.radio("Language", ["English", "മലയാളം"], horizontal=True)
lang = "ml" if lang_label == "മലയാളം" else "en"

planting_date = st.date_input(
    "Planting date",
    value=date.today(),
)

if crop.strip().lower() not in DEFAULT_GROWTH_DAYS:
    st.caption("Estimate whether a crop's price may rise or fall by its expected harvest month.")

growth_days = st.number_input(
    "Expected growing time (days)",
    min_value=1,
    max_value=2000,
    value=DEFAULT_GROWTH_DAYS.get(crop.strip().lower(), 120),
    step=1,
    placeholder="Enter the expected number of days",
    key=f"growth_days_{crop.strip().lower().replace(' ', '_')}",
    help="This is an approximate crop-specific default. Adjust it for your crop variety and growing conditions.",
)

if growth_days is not None:
    harvest_date = planting_date + timedelta(days=int(growth_days))
    st.info(f"Estimated harvest date: {harvest_date:%d %B %Y}")

if growth_days is None:
    st.info("Enter the expected growing time to calculate a harvest date.")
    st.stop()

# --- Load Data & Forecast ---
df, source = _load(crop)
latest_price_date = pd.to_datetime(df["date"], errors="coerce").max()

if pd.isna(latest_price_date):
    st.error("Could not find valid dates in the price data.")
    st.stop()

horizon = (
    (harvest_date.year - latest_price_date.year) * 12
    + harvest_date.month - latest_price_date.month
)

if horizon < 1:
    st.error("The estimated harvest month must be after the latest price-data month.")
    st.stop()

if horizon > 12:
    st.warning("This forecast currently supports harvest dates up to 12 months ahead.")
    st.stop()

st.caption(f"Forecasting {horizon} month(s) ahead, for the estimated harvest month.")

if source == "demo":
    st.error("🧪 DEMO DATA: no real price history for this crop yet. "
             "Numbers below are synthetic and for illustration only.")

try:
    res = forecast_price_trend(df, crop, horizon)
except InsufficientDataError as e:
    st.info(str(e))
    st.stop()

icon = {"RISE": "⬆️", "FALL": "⬇️", "STABLE": "➡️"}[res.direction]
m1, m2, m3, m4 = st.columns(4)
m1.metric("Current price (₹/quintal)", f"{res.last_price:,.0f}")
m2.metric("Estimated price at harvest", f"₹{res.target_price:,.0f}/quintal", f"{res.pct_change:+.1%}")
m3.metric("Estimated direction", f"{icon} {res.direction}")
m4.metric("Confidence", res.confidence)

# ---- chart: history + forecast + 80% band ----
hist = res.history.assign(kind="Past price")
fc = res.forecast
bridge = pd.DataFrame({"date": [hist["date"].iloc[-1]], "price": [hist["price"].iloc[-1]]})
fline = pd.concat([bridge, fc[["date", "price"]]]).assign(kind="Estimate")
band = alt.Chart(fc).mark_area(opacity=0.2).encode(
    x="date:T", y=alt.Y("low:Q", title="₹ per quintal"), y2="high:Q")
line = alt.Chart(pd.concat([hist, fline])).mark_line(point=True).encode(
    x=alt.X("date:T", title=None), y="price:Q",
    color=alt.Color("kind:N", title=None),
    strokeDash=alt.condition(alt.datum.kind == "Estimate", alt.value([5, 4]), alt.value([0])))
st.altair_chart((band + line).properties(height=380), use_container_width=True)
st.caption("Shaded area = likely range (about 80% chance). Dashed line = estimate.")

# ---- plain-language explanation ----
groq_key = st.secrets.get("GROQ_API_KEY") if hasattr(st, "secrets") else None
with st.spinner("Preparing explanation..."):
    st.info(explain_forecast(res, lang, groq_key))

# ---- transparency ----
with st.expander("How reliable is this? (details)"):
    st.write(f"- Months of price data used: **{res.n_months}**")
    st.write(f"- Seasonal pattern used: **{'Yes' if res.used_seasonality else 'No'}**")
    if res.backtest:
        b = res.backtest
        st.write(f"- Past test: direction was right **{b['directional_accuracy']:.0%}** of the time "
                 f"over {b['n_tests']} tests (guessing “no change” would score {b['baseline_accuracy']:.0%}).")
        st.write(f"- Average price error in past tests: **{b['mape']:.0%}**")
    for n in res.notes:
        st.write(f"- ⚠️ {n}")
    st.caption(res.disclaimer)