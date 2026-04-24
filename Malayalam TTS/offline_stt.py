"""
Offline Malayalam Speech-to-Text (STT) using Vosk
==================================================
Fully offline — no internet required.
Uses a local Vosk Malayalam model and PyAudio for real-time
microphone capture with VAD-based automatic stop.
"""

import os
import sys
import json
import struct
import logging

import pyaudio
from vosk import Model, KaldiRecognizer, SetLogLevel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_PATH = os.getenv("VOSK_ML_MODEL_PATH", "vosk-model-ml-0.22")
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2           # 16-bit PCM (2 bytes per sample)
CHUNK_FRAMES = 4000        # ~250 ms at 16 kHz
FORMAT = pyaudio.paInt16

# VAD parameters
RMS_SILENCE_THRESHOLD = 200       # RMS below this is "silence"
SILENCE_CHUNKS_TO_STOP = 12       # consecutive silent chunks → stop (~3 s)
MIN_SPEECH_CHUNKS = 4             # minimum voiced chunks before VAD can trigger

# Suppress Vosk internal logs (set to 0 for debug, -1 for silent)
SetLogLevel(-1)


# ---------------------------------------------------------------------------
# Model Loader
# ---------------------------------------------------------------------------
_model_instance = None


def _get_model() -> Model:
    """Load and cache the Vosk Malayalam model from a local directory."""
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    model_path = os.path.abspath(MODEL_PATH)
    if not os.path.isdir(model_path):
        logger.error(
            "Vosk model directory not found: '%s'. "
            "Download it from https://alphacephei.com/vosk/models and "
            "extract to this path, or set VOSK_ML_MODEL_PATH env var.",
            model_path,
        )
        sys.exit(1)

    logger.info("Loading Vosk Malayalam model from: %s", model_path)
    _model_instance = Model(model_path)
    logger.info("Model loaded successfully.")
    return _model_instance


# ---------------------------------------------------------------------------
# RMS helper (pure stdlib — no numpy dependency)
# ---------------------------------------------------------------------------

def _rms(data: bytes) -> float:
    """Compute RMS amplitude of a 16-bit PCM audio chunk."""
    count = len(data) // SAMPLE_WIDTH
    if count == 0:
        return 0.0
    fmt = f"<{count}h"  # little-endian signed 16-bit
    samples = struct.unpack(fmt, data)
    sum_sq = sum(s * s for s in samples)
    return (sum_sq / count) ** 0.5


# ---------------------------------------------------------------------------
# Core Function
# ---------------------------------------------------------------------------

def listen_and_transcribe_offline() -> str:
    """
    Capture live microphone audio and transcribe to Malayalam text offline.

    Behaviour:
        1. Opens the default mic at 16 kHz mono.
        2. Streams audio into the Vosk recogniser.
        3. Prints partial results in real-time.
        4. Uses RMS-based VAD to detect when the speaker stops talking.
        5. Returns the final transcription string.

    Returns:
        Transcribed Malayalam text (UTF-8).
    """
    model = _get_model()
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    recognizer.SetWords(True)

    pa = pyaudio.PyAudio()
    stream = None

    try:
        stream = pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_FRAMES,
        )
        stream.start_stream()

        logger.info("🎙️  മൈക്രോഫോൺ സജ്ജമാണ്. സംസാരിക്കൂ...")
        logger.info("    (Microphone ready. Start speaking in Malayalam...)")

        silent_chunks = 0
        speech_chunks = 0
        full_text_parts = []

        while True:
            data = stream.read(CHUNK_FRAMES, exception_on_overflow=False)

            # --- VAD: track speech / silence ---
            amplitude = _rms(data)

            if amplitude < RMS_SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0
                speech_chunks += 1

            # Feed audio to recogniser
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    # UTF-8 safety
                    text = text.encode("utf-8").decode("utf-8")
                    full_text_parts.append(text)
                    logger.info("📝 [Final]   %s", text)
            else:
                partial = json.loads(recognizer.PartialResult())
                partial_text = partial.get("partial", "").strip()
                if partial_text:
                    print(f"\r⏳ {partial_text}", end="", flush=True)

            # --- VAD stop condition ---
            if (
                speech_chunks >= MIN_SPEECH_CHUNKS
                and silent_chunks >= SILENCE_CHUNKS_TO_STOP
            ):
                logger.info("⏹️  Silence detected — ending capture.")
                break

        # Flush any remaining audio in the recogniser
        final = json.loads(recognizer.FinalResult())
        final_text = final.get("text", "").strip()
        if final_text:
            final_text = final_text.encode("utf-8").decode("utf-8")
            full_text_parts.append(final_text)
            logger.info("📝 [Final]   %s", final_text)

        print()  # clear the partial-result line
        transcript = " ".join(full_text_parts).strip()
        return transcript

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        return " ".join(full_text_parts).strip() if "full_text_parts" in dir() else ""

    except Exception as exc:
        logger.error("STT error: %s", exc, exc_info=True)
        raise RuntimeError(f"Offline STT failed: {exc}") from exc

    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        pa.terminate()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = listen_and_transcribe_offline()
    print("\n" + "=" * 60)
    print("മലയാളം ട്രാൻസ്ക്രിപ്ഷൻ (Offline Transcription)")
    print("=" * 60)
    print(result if result else "(No speech detected)")
    print("=" * 60)
