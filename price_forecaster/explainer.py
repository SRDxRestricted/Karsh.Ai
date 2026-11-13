"""Plain-language explanation of a forecast (English / Malayalam). Uses Groq if a key exists."""
from __future__ import annotations

from .forecaster import ForecastResult

_ARROW = {"RISE": "⬆️ may RISE", "FALL": "⬇️ may FALL", "STABLE": "➡️ may stay about the SAME"}
_ARROW_ML = {"RISE": "⬆️ കൂടാൻ സാധ്യത", "FALL": "⬇️ കുറയാൻ സാധ്യത", "STABLE": "➡️ ഏതാണ്ട് മാറ്റമില്ലാതെ തുടരാൻ സാധ്യത"}


def _facts(r: ForecastResult) -> str:
    return (
        f"Crop: {r.crop}. Current price about Rs {r.last_price:,.0f}/quintal. "
        f"Estimated price in {r.horizon} month(s): Rs {r.target_price:,.0f} "
        f"({r.pct_change:+.1%}), likely range Rs {r.forecast['low'].iloc[-1]:,.0f} to "
        f"Rs {r.forecast['high'].iloc[-1]:,.0f}. Direction: {r.direction}. "
        f"Confidence: {r.confidence}. Months of data used: {r.n_months}. "
        f"Seasonality used: {r.used_seasonality}. Notes: {' '.join(r.notes) or 'none'}."
    )


def _template(r: ForecastResult, lang: str) -> str:
    if lang == "ml":
        return (f"**{r.crop}** വില അടുത്ത {r.horizon} മാസത്തിൽ {_ARROW_ML[r.direction]} "
                f"({r.pct_change:+.1%}). ഇത് മുൻകാല വിലകളെ അടിസ്ഥാനമാക്കിയുള്ള ഒരു **ഏകദേശ കണക്ക്** മാത്രമാണ്, "
                f"ഉറപ്പില്ല. വിശ്വാസ്യത: {r.confidence}.")
    return (f"**{r.crop}** prices {_ARROW[r.direction]} over the next {r.horizon} month(s) "
            f"({r.pct_change:+.1%}). This is only an **estimate** from past prices, not a promise. "
            f"Confidence: **{r.confidence}**.")


def explain_forecast(r: ForecastResult, lang: str = "en", groq_api_key: str | None = None) -> str:
    """lang: 'en' or 'ml'. Falls back to a fixed template if Groq is unavailable."""
    if not groq_api_key:
        return _template(r, lang)
    try:
        from groq import Groq

        language = "Malayalam" if lang == "ml" else "simple English"
        client = Groq(api_key=groq_api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=300,
            messages=[
                {"role": "system", "content": (
                    "You explain crop price estimates to small farmers in India. "
                    f"Reply in {language}, max 4 short sentences. Use ONLY the facts given. "
                    "Always call it an estimate, mention the confidence, never promise a price, "
                    "and never tell the farmer to buy or sell.")},
                {"role": "user", "content": _facts(r)},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return _template(r, lang)
