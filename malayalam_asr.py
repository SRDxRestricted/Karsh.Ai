"""
Malayalam Automatic Speech Recognition (ASR) Module
====================================================
Uses faster-whisper with forced Malayalam language detection
and pydub-based audio pre-processing for noisy farm environments.
"""

import os
import tempfile
import logging
from pathlib import Path

from faster_whisper import WhisperModel
from pydub import AudioSegment
from pydub.effects import normalize, low_pass_filter, high_pass_filter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_SIZE = "large-v3"          # Options: "medium", "large-v3"
DEVICE = "auto"                  # "cpu", "cuda", or "auto"
COMPUTE_TYPE = "int8"            # "float16" for GPU, "int8" for CPU

# Audio pre-processing constants
TARGET_SAMPLE_RATE = 16000       # Whisper expects 16 kHz mono
HIGH_PASS_CUTOFF = 300           # Hz – removes low-frequency rumble (wind, tractor)
LOW_PASS_CUTOFF = 3400           # Hz – removes high-frequency hiss
SILENCE_THRESH_DB = -40          # dBFS threshold for silence trimming
SILENCE_PADDING_MS = 300         # ms of silence to keep at edges after trimming

# Singleton model instance (loaded once, reused across calls)
_model_instance: WhisperModel | None = None


def _get_model() -> WhisperModel:
    """Lazily load and cache the Whisper model."""
    global _model_instance
    if _model_instance is None:
        logger.info("Loading faster-whisper model '%s' (device=%s, compute=%s)...",
                     MODEL_SIZE, DEVICE, COMPUTE_TYPE)
        _model_instance = WhisperModel(
            MODEL_SIZE,
            device=DEVICE,
            compute_type=COMPUTE_TYPE,
        )
        logger.info("Model loaded successfully.")
    return _model_instance


# ---------------------------------------------------------------------------
# Audio Pre-processing
# ---------------------------------------------------------------------------
def preprocess_audio(audio_path: str) -> str:
    """
    Pre-process raw field audio for optimal ASR accuracy.

    Steps:
        1. Load any supported format (wav, mp3, ogg, m4a, webm, etc.)
        2. Convert to mono 16 kHz (Whisper's expected input).
        3. Apply high-pass filter to remove wind / tractor rumble.
        4. Apply low-pass filter to remove high-frequency hiss.
        5. Normalize volume levels to compensate for varying mic distances.
        6. Trim leading/trailing silence.

    Returns the path to a cleaned temporary WAV file.
    """
    logger.info("Pre-processing audio: %s", audio_path)

    # Load audio (pydub auto-detects format via ffmpeg)
    audio = AudioSegment.from_file(audio_path)

    # Step 1 – Convert to mono, 16 kHz
    audio = audio.set_channels(1).set_frame_rate(TARGET_SAMPLE_RATE)

    # Step 2 – Band-pass filtering (high-pass + low-pass)
    audio = high_pass_filter(audio, cutoff=HIGH_PASS_CUTOFF)
    audio = low_pass_filter(audio, cutoff=LOW_PASS_CUTOFF)

    # Step 3 – Normalize volume
    audio = normalize(audio)

    # Step 4 – Trim silence from edges
    def _trim_silence(seg: AudioSegment) -> AudioSegment:
        """Remove leading and trailing silence while keeping a small pad."""
        start_trim = _detect_leading_silence(seg)
        end_trim = _detect_leading_silence(seg.reverse())
        start = max(0, start_trim - SILENCE_PADDING_MS)
        end = max(0, end_trim - SILENCE_PADDING_MS)
        duration = len(seg)
        return seg[start:duration - end]

    audio = _trim_silence(audio)

    # Export to temporary WAV
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio.export(tmp.name, format="wav")
    logger.info("Pre-processed audio saved to: %s (duration=%.1fs)", tmp.name, len(audio) / 1000)
    return tmp.name


def _detect_leading_silence(sound: AudioSegment, chunk_size: int = 10) -> int:
    """Return milliseconds of leading silence in an AudioSegment."""
    trim_ms = 0
    while trim_ms < len(sound) and sound[trim_ms:trim_ms + chunk_size].dBFS < SILENCE_THRESH_DB:
        trim_ms += chunk_size
    return trim_ms


# ---------------------------------------------------------------------------
# Core ASR Function
# ---------------------------------------------------------------------------
def transcribe_malayalam(audio_path: str) -> str:
    """
    Transcribe a Malayalam audio file to text.

    Args:
        audio_path: Path to the input audio file (any format supported by ffmpeg).

    Returns:
        The transcribed Malayalam text as a single string.

    Raises:
        FileNotFoundError: If the audio file does not exist.
        RuntimeError: If transcription fails.
    """
    audio_path = str(Path(audio_path).resolve())
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Pre-process audio for noisy outdoor environments
    cleaned_path = preprocess_audio(audio_path)

    try:
        model = _get_model()

        # ------------------------------------------------------------------
        # CRITICAL: Force language="ml" (Malayalam ISO 639-1 code).
        # Without this, Whisper often misidentifies 'Manglish'
        # (Malayalam written in Latin script) as English and produces
        # garbage transliterations.
        # ------------------------------------------------------------------
        segments, info = model.transcribe(
            cleaned_path,
            language="ml",               # Force Malayalam
            task="transcribe",           # Transcribe, not translate
            beam_size=5,                 # Higher beam = better accuracy
            best_of=5,                   # Sample multiple candidates
            temperature=0.0,             # Greedy decoding for consistency
            condition_on_previous_text=True,
            vad_filter=True,             # Voice Activity Detection filter
            vad_parameters={
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 200,
            },
        )

        logger.info(
            "Detected language: %s (probability=%.2f)",
            info.language,
            info.language_probability,
        )

        # Collect all segment texts
        transcript_parts = []
        for segment in segments:
            logger.debug("[%.2fs -> %.2fs] %s", segment.start, segment.end, segment.text)
            transcript_parts.append(segment.text.strip())

        transcript = " ".join(transcript_parts).strip()

        if not transcript:
            logger.warning("Transcription returned empty text for: %s", audio_path)
            return ""

        logger.info("Transcription complete (%d chars): %s...",
                     len(transcript), transcript[:80])
        return transcript

    except Exception as e:
        logger.error("Transcription failed: %s", e)
        raise RuntimeError(f"Transcription failed: {e}") from e

    finally:
        # Clean up temporary pre-processed file
        if os.path.exists(cleaned_path) and cleaned_path != audio_path:
            os.unlink(cleaned_path)
            logger.debug("Cleaned up temp file: %s", cleaned_path)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python malayalam_asr.py <audio_file_path>")
        print("       Supports: .wav, .mp3, .ogg, .m4a, .webm, .flac")
        sys.exit(1)

    input_path = sys.argv[1]
    result = transcribe_malayalam(input_path)
    print("\n" + "=" * 60)
    print("മലയാളം ട്രാൻസ്ക്രിപ്ഷൻ (Malayalam Transcription)")
    print("=" * 60)
    print(result)
    print("=" * 60)
