"""
English-to-Malayalam Speech Module
===================================
Translates English text to Malayalam via deep-translator (GoogleTranslator)
and synthesises Malayalam audio output using gTTS.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from deep_translator import GoogleTranslator
from gtts import gTTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Translation constants
_SOURCE_LANG = "en"
_TARGET_LANG = "ml"
_GTTS_LANG = "ml"
_TRANSLATOR_TIMEOUT = 15  # seconds


def speak_malayalam_from_english(
    english_text: str,
    output_path: str = "response.mp3",
    slow: bool = False,
) -> str:
    """
    Translate an English string to Malayalam and save as spoken audio.

    Args:
        english_text: Input text in English.
        output_path:  Destination file path (.mp3).
        slow:         If True, gTTS produces slower speech
                      (useful for elderly listeners).

    Returns:
        Absolute path to the saved audio file.

    Raises:
        ValueError:  If the input text is empty or not a string.
        RuntimeError: If translation or TTS fails.
    """
    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    try:
        if not isinstance(english_text, str):
            raise ValueError(f"Expected str, got {type(english_text).__name__}")

        english_text = english_text.strip()
        if not english_text:
            raise ValueError("Input text must not be empty.")

    except ValueError:
        raise

    # ------------------------------------------------------------------
    # Step 1: Translate English → Malayalam
    # ------------------------------------------------------------------
    malayalam_text: Optional[str] = None

    try:
        translator = GoogleTranslator(source=_SOURCE_LANG, target=_TARGET_LANG)
        malayalam_text = translator.translate(english_text)

        # UTF-8 round-trip to guard against encoding corruption
        malayalam_text = malayalam_text.encode("utf-8").decode("utf-8").strip()

        if not malayalam_text:
            raise RuntimeError("Translator returned an empty string.")

        logger.info(
            "Translation complete: '%s' → '%s'",
            english_text[:60],
            malayalam_text[:60],
        )

    except RuntimeError:
        raise
    except Exception as exc:
        logger.error("Translation failed: %s", exc)
        raise RuntimeError(
            f"English→Malayalam translation failed: {exc}"
        ) from exc

    # ------------------------------------------------------------------
    # Step 2: Malayalam text → speech (gTTS)
    # ------------------------------------------------------------------
    try:
        tts = gTTS(
            text=malayalam_text,
            lang=_GTTS_LANG,
            slow=slow,
            lang_check=False,
        )

        output_path = str(Path(output_path).resolve())
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        tts.save(output_path)
        logger.info("Audio saved: %s", output_path)
        return output_path

    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        raise RuntimeError(
            f"Malayalam TTS synthesis failed: {exc}"
        ) from exc
