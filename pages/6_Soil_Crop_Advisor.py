import html
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth import KERALA_DISTRICTS, get_user_district, get_username, require_auth
from soil_advisor.model import ensure_model, get_metadata, predict_crops
from soil_advisor.storage import load_recent_readings, save_reading
from soil_advisor.validation import (
    FEATURE_LABELS,
    MG_PER_KG_TO_KG_PER_HA,
    NPK_UNITS,
    SoilInput,
    outside_training_range,
)
from theme import init_theme, inject_global_css, render_sidebar

st.set_page_config(
    page_title="Karsh.Ai | Soil Advisor",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_theme()
inject_global_css()
require_auth()
render_sidebar()

SOIL_TYPES = ["Loamy", "Clay", "Sandy", "Red", "Laterite", "Alluvial", "Not sure"]


def _match_label(probability: float) -> str:
    if probability >= 50:
        return "Strong match"
    if probability >= 25:
        return "Good match"
    if probability >= 10:
        return "Possible match"
    return "Low confidence"


st.markdown("### Soil & Crop Advisor")
st.markdown(
    "Enter your soil test values and local climate. The model compares them with "
    "Kerala crop profiles and ranks the crops that fit best."
)
st.caption(
    f"N, P and K are plant-available nutrients. 1 mg/kg is roughly "
    f"{MG_PER_KG_TO_KG_PER_HA:g} kg/ha in a 0–15 cm soil layer."
)

metadata = get_metadata()
if metadata and str(metadata.get("dataset_source", "")).startswith("synthetic"):
    st.caption(
        "Demo model: trained on synthetic Kerala crop profiles. "
        "Add measured data to `data/crop_recommendation.csv` and retrain."
    )

default_district = get_user_district()
try:
    district_index = KERALA_DISTRICTS.index(default_district)
except ValueError:
    district_index = 6

with st.form("soil_advisor_form"):
    st.markdown("#### Soil test values")
    unit = st.radio(
        "NPK unit",
        NPK_UNITS,
        horizontal=True,
        index=0,
        help="Use the unit printed on your soil health card.",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        nitrogen = st.number_input(
            "Nitrogen (N)", min_value=0.0, max_value=650.0, value=80.0, step=1.0,
            help="Plant-available nitrogen.",
        )
    with c2:
        phosphorus = st.number_input(
            "Phosphorus (P)", min_value=0.0, max_value=650.0, value=45.0, step=1.0,
            help="Plant-available phosphorus.",
        )
    with c3:
        potassium = st.number_input(
            "Potassium (K)", min_value=0.0, max_value=650.0, value=50.0, step=1.0,
            help="Plant-available potassium.",
        )
    with c4:
        ph = st.number_input(
            "Soil pH", min_value=0.0, max_value=14.0, value=6.5, step=0.1,
            format="%.1f", help="7 is neutral; below 7 is acidic.",
        )

    st.markdown("#### Climate & site")
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        temperature = st.number_input(
            "Temperature (°C)", min_value=-10.0, max_value=55.0, value=27.0, step=0.5,
            format="%.1f",
        )
    with c6:
        humidity = st.number_input(
            "Humidity (%)", min_value=0.0, max_value=100.0, value=80.0, step=1.0,
        )
    with c7:
        rainfall = st.number_input(
            "Seasonal rainfall (mm)", min_value=0.0, max_value=1000.0, value=200.0, step=10.0,
            help="Approximate rainfall during the growing season.",
        )
    with c8:
        land_area = st.number_input(
            "Land area (hectares)", min_value=0.0, max_value=10_000.0, value=1.0, step=0.1,
            format="%.1f", help="Optional; used only to give context to the recommendation.",
        )

    c9, c10 = st.columns(2)
    with c9:
        district = st.selectbox("District", KERALA_DISTRICTS, index=district_index)
    with c10:
        soil_type = st.selectbox("Soil type", SOIL_TYPES, index=0)

    submitted = st.form_submit_button(
        "Recommend crops", use_container_width=True, type="primary"
    )

if submitted:
    try:
        soil = SoilInput(
            N=nitrogen,
            P=phosphorus,
            K=potassium,
            temperature=temperature,
            humidity=humidity,
            ph=ph,
            rainfall=rainfall,
            district=district,
            soil_type=soil_type,
            land_area_ha=land_area or None,
            npk_unit=unit,
        )
        soil.validate()
        features = soil.to_features()

        with st.spinner("Loading the soil model..."):
            model, metadata = ensure_model()

        result = predict_crops(features, top_k=3, model=model, metadata=metadata)
        result["warnings"] = outside_training_range(
            features, metadata.get("training_ranges", {})
        )
        result["features"] = features
        result["input"] = {
            "N": nitrogen,
            "P": phosphorus,
            "K": potassium,
            "temperature": temperature,
            "humidity": humidity,
            "ph": ph,
            "rainfall": rainfall,
            "npk_unit": unit,
            "district": district,
            "soil_type": soil_type,
            "land_area_ha": land_area,
        }
        st.session_state["soil_result"] = result

        try:
            save_reading(
                get_username(),
                district,
                soil_type,
                features,
                result,
                metadata.get("model_version"),
            )
        except OSError:
            pass

    except ValueError as exc:
        st.session_state.pop("soil_result", None)
        st.error(str(exc))
    except Exception as exc:
        st.session_state.pop("soil_result", None)
        st.error(f"Could not run the soil model: {exc}")

result = st.session_state.get("soil_result")
if result:
    if result.get("warnings"):
        st.warning(
            "Some values are outside the model's training range, so treat this "
            "result as indicative:\n\n- " + "\n- ".join(result["warnings"])
        )

    st.markdown("### Recommended crops")
    st.caption(
        f"Model {result.get('model_version', '—')} · "
        f"data source: {result.get('dataset_source', '—')}"
    )

    for rank, prediction in enumerate(result.get("predictions", []), start=1):
        name = html.escape(str(prediction.get("display_name", prediction.get("crop", ""))))
        malayalam = html.escape(str(prediction.get("malayalam_name", "")))
        probability = float(prediction.get("probability", 0.0))
        malayalam_html = (
            f"<div style='color:#9e9eb8;font-size:0.82rem;margin-top:2px;'>{malayalam}</div>"
            if malayalam
            else ""
        )
        st.markdown(
            f"""
            <div style='background:#1e1e36;border:1px solid #2a2a4a;border-radius:14px;padding:20px;margin-bottom:14px;'>
                <div style='display:flex;align-items:flex-start;gap:18px;'>
                    <div style='font-size:1.8rem;font-weight:900;color:#9e9eb8;min-width:46px;'>#{rank}</div>
                    <div style='flex:1;'>
                        <div style='font-size:1.1rem;font-weight:700;color:#e0e0e0;'>{name}</div>
                        {malayalam_html}
                        <div class='conf-bg'><div class='conf-fill' style='width:{probability}%;'></div></div>
                        <div style='color:#9e9eb8;font-size:0.8rem;'>
                            Model confidence: {probability:.1f}% · {_match_label(probability)}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Why these crops?"):
        st.markdown("**Your inputs (converted to the model's units):**")
        input_rows = [
            {"Feature": FEATURE_LABELS.get(key, key), "Value": round(float(value), 2)}
            for key, value in result.get("features", {}).items()
        ]
        st.dataframe(pd.DataFrame(input_rows), use_container_width=True, hide_index=True)

        importance = result.get("top_feature_importance", {})
        if importance:
            st.markdown("**What the model relies on most:**")
            importance_rows = [
                {"Feature": FEATURE_LABELS.get(key, key), "Importance": f"{float(value):.1%}"}
                for key, value in list(importance.items())[:5]
            ]
            st.dataframe(
                pd.DataFrame(importance_rows), use_container_width=True, hide_index=True
            )

        st.caption(
            "Confidence is the model's probability for each crop, not a guarantee. "
            "A soil test from an accredited lab is the best basis for a decision."
        )

if metadata:
    with st.expander("Model details and data source"):
        source = str(metadata.get("dataset_source", ""))
        if source.startswith("synthetic"):
            st.warning(
                "This demo model is trained on synthetic Kerala crop profiles. "
                "Replace data/crop_recommendation.csv with measured soil data for "
                "production use."
            )
        else:
            st.info(f"Trained on {source}.")

        metrics = metadata.get("metrics", {})
        m1, m2, m3 = st.columns(3)
        m1.metric("Accuracy", f"{float(metrics.get('accuracy', 0)):.1%}")
        m2.metric("Macro F1", f"{float(metrics.get('macro_f1', 0)):.1%}")
        m3.metric("Top-3 accuracy", f"{float(metrics.get('top3_accuracy', 0)):.1%}")
        st.caption(
            f"Version {metadata.get('model_version', '—')} · "
            f"trained {metadata.get('trained_at', '—')} · "
            f"{metadata.get('dataset_rows', '—')} rows · "
            f"{metadata.get('train_test_split', '—')} split"
        )
        st.caption(
            "Retrain with `python -m soil_advisor.train`. "
            "The model file and metadata live in the gitignored `models/` folder."
        )
else:
    st.info(
        "The model trains automatically on your first recommendation. "
        "You can also run `python -m soil_advisor.train`."
    )

recent_readings = load_recent_readings(get_username(), limit=5)
if recent_readings:
    with st.expander("Recent soil checks"):
        for record in recent_readings:
            predictions = record.get("predictions") or []
            top_prediction = predictions[0] if predictions else {}
            created = str(record.get("created_at", ""))[:10]
            st.markdown(
                f"**{created}** · {record.get('district', '—')} · "
                f"{top_prediction.get('display_name', 'No result')} "
                f"({float(top_prediction.get('probability', 0)):.1f}%)"
            )

st.markdown("---")
st.caption(
    "Advisory only. The recommendation reflects patterns in the training data and "
    "does not replace a soil test, local extension advice, or your own judgement."
)
