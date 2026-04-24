"""
Malayalam Text-to-Speech Synthesizer
=====================================
Primary: Bhashini API (ULCA-compliant Indian government TTS pipeline)
Fallback: gTTS (Google Translate TTS)

Fully Unicode / UTF-8 compatible for Malayalam script (U+0D00–U+0D7F).
"""

import io
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

import requests
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class MalayalamSynthesizer:
    """
    High-quality Malayalam text-to-speech synthesizer.

    Prioritises the Bhashini API for natural Indian-language speech.
    Falls back to gTTS automatically when Bhashini is unreachable.

    Args:
        bhashini_api_key:   Bhashini / ULCA API key (optional; reads
                            BHASHINI_API_KEY env var if not provided).
        bhashini_user_id:   Bhashini user ID (optional; reads
                            BHASHINI_USER_ID env var if not provided).
        speaking_rate:      Playback speed multiplier.
                            1.0 = normal, 0.75 = slower (elderly-friendly),
                            1.25 = faster. Range: 0.5–2.0.
        default_format:     Output format — "mp3" or "wav".
        bhashini_timeout:   Seconds to wait for Bhashini before falling back.
    """

    # Bhashini ULCA pipeline endpoints
    _BHASHINI_PIPELINE_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
    _BHASHINI_COMPUTE_URL_PLACEHOLDER = None  # resolved dynamically per pipeline

    # Supported speaking-rate bounds
    _MIN_RATE = 0.5
    _MAX_RATE = 2.0

    def __init__(
        self,
        bhashini_api_key: Optional[str] = None,
        bhashini_user_id: Optional[str] = None,
        speaking_rate: float = 1.0,
        default_format: str = "mp3",
        bhashini_timeout: int = 10,
    ) -> None:
        self.bhashini_api_key = bhashini_api_key or os.getenv("BHASHINI_API_KEY", "")
        self.bhashini_user_id = bhashini_user_id or os.getenv("BHASHINI_USER_ID", "")
        self.speaking_rate = self._clamp_rate(speaking_rate)
        self.default_format = default_format.lower().strip(".")
        self.bhashini_timeout = bhashini_timeout

        # Cached Bhashini pipeline config (resolved on first call)
        self._pipeline_config: Optional[dict] = None
        self._bhashini_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def speak(self, text: str, output_file: str, speaking_rate: Optional[float] = None) -> str:
        """
        Synthesise Malayalam speech and save to a file.

        Args:
            text:           Malayalam text (Unicode UTF-8).
            output_file:    Destination path (.mp3 or .wav).
            speaking_rate:  Override instance-level rate for this call.

        Returns:
            Absolute path to the saved audio file.

        Raises:
            ValueError:  If text is empty or not a string.
            RuntimeError: If both Bhashini and gTTS fail.
        """
        text = self._validate_and_clean(text)
        rate = self._clamp_rate(speaking_rate) if speaking_rate is not None else self.speaking_rate
        output_file = str(Path(output_file).resolve())
        fmt = self._format_from_path(output_file)

        logger.info("TTS request: %d chars, rate=%.2f, format=%s", len(text), rate, fmt)

        audio_bytes: Optional[bytes] = None

        # --- Attempt 1: Bhashini API ---
        if self._is_bhashini_configured():
            try:
                audio_bytes = self._synthesize_bhashini(text, rate)
                logger.info("Bhashini TTS succeeded.")
            except Exception as exc:
                logger.warning("Bhashini TTS failed (%s). Falling back to gTTS.", exc)
                audio_bytes = None

        # --- Attempt 2: gTTS fallback ---
        if audio_bytes is None:
            try:
                audio_bytes = self._synthesize_gtts(text, rate)
                logger.info("gTTS fallback succeeded.")
            except Exception as exc:
                logger.error("gTTS fallback also failed: %s", exc)
                raise RuntimeError(
                    "Both Bhashini and gTTS failed. Check network connectivity."
                ) from exc

        # --- Post-process & save ---
        self._save_audio(audio_bytes, output_file, fmt, rate)
        logger.info("Audio saved: %s", output_file)
        return output_file

    def set_speaking_rate(self, rate: float) -> None:
        """Update the default speaking rate."""
        self.speaking_rate = self._clamp_rate(rate)
        logger.info("Speaking rate set to %.2f", self.speaking_rate)

    # ------------------------------------------------------------------
    # Bhashini API Integration
    # ------------------------------------------------------------------

    def _is_bhashini_configured(self) -> bool:
        """Check if Bhashini credentials are available."""
        return bool(self.bhashini_api_key and self.bhashini_user_id)

    def _resolve_bhashini_pipeline(self) -> dict:
        """
        Call the ULCA pipeline discovery endpoint to get the
        TTS service URL and model ID for Malayalam.
        """
        if self._pipeline_config is not None:
            return self._pipeline_config

        headers = {
            "Content-Type": "application/json",
            "ulcaApiKey": self.bhashini_api_key,
            "userID": self.bhashini_user_id,
        }
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": "ml"},
                    },
                }
            ],
            "pipelineRequestConfig": {
                "pipelineId": "64392f96daac500b55c543cd",
            },
        }

        resp = requests.post(
            self._BHASHINI_PIPELINE_URL,
            json=payload,
            headers=headers,
            timeout=self.bhashini_timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract compute URL and auth key
        pipeline_inference = data["pipelineInferenceAPIEndPoint"]
        callback_url = pipeline_inference["callbackUrl"]
        inference_key = (
            pipeline_inference["inferenceApiKey"]["value"]
        )

        # Extract TTS model config
        tts_configs = data["pipelineResponseConfig"][0]["config"]
        service_id = tts_configs[0]["serviceId"]
        model_id = tts_configs[0].get("modelId", "")

        self._pipeline_config = {
            "callback_url": callback_url,
            "inference_key": inference_key,
            "service_id": service_id,
            "model_id": model_id,
        }
        logger.info("Bhashini pipeline resolved: service=%s", service_id)
        return self._pipeline_config

    def _synthesize_bhashini(self, text: str, rate: float) -> bytes:
        """
        Call Bhashini TTS inference endpoint.

        Returns raw audio bytes (WAV).
        """
        config = self._resolve_bhashini_pipeline()

        headers = {
            "Content-Type": "application/json",
            "Authorization": config["inference_key"],
        }

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": "ml"},
                        "serviceId": config["service_id"],
                        "gender": "female",
                        "samplingRate": 22050,
                    },
                }
            ],
            "inputData": {
                "input": [{"source": text}],
            },
        }

        resp = requests.post(
            config["callback_url"],
            json=payload,
            headers=headers,
            timeout=self.bhashini_timeout + 10,
        )
        resp.raise_for_status()
        result = resp.json()

        # Bhashini returns base64-encoded audio
        import base64
        audio_b64 = result["pipelineResponse"][0]["audio"][0]["audioContent"]
        audio_bytes = base64.b64decode(audio_b64)
        return audio_bytes

    # ------------------------------------------------------------------
    # gTTS Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _synthesize_gtts(text: str, rate: float) -> bytes:
        """
        Synthesise using Google Translate TTS (gTTS).

        gTTS doesn't support rate control natively; rate adjustment
        is handled in post-processing via pydub.

        Returns raw MP3 bytes.
        """
        from gtts import gTTS

        tts = gTTS(
            text=text,
            lang="ml",        # Malayalam
            slow=False,       # We handle rate in post-processing
            lang_check=False, # Skip language validation (ml is supported)
        )

        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return buffer.read()

    # ------------------------------------------------------------------
    # Audio Post-processing & File I/O
    # ------------------------------------------------------------------

    def _save_audio(self, audio_bytes: bytes, output_file: str, fmt: str, rate: float) -> None:
        """
        Post-process audio (rate adjustment) and save to the target format.
        """
        # Load into pydub for manipulation
        buffer = io.BytesIO(audio_bytes)

        # Try loading as mp3 first (gTTS output), then as wav (Bhashini output)
        audio = self._load_audio_segment(buffer)

        # Adjust speaking rate via playback speed change
        if abs(rate - 1.0) > 0.05:
            audio = self._adjust_rate(audio, rate)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)

        # Export
        export_params = {}
        if fmt == "mp3":
            export_params = {"format": "mp3", "bitrate": "192k"}
        else:
            export_params = {"format": "wav"}

        audio.export(output_file, **export_params)

    @staticmethod
    def _load_audio_segment(buffer: io.BytesIO) -> AudioSegment:
        """Try multiple formats when loading audio bytes."""
        for fmt in ("mp3", "wav", "ogg", "raw"):
            try:
                buffer.seek(0)
                if fmt == "raw":
                    return AudioSegment.from_raw(
                        buffer, sample_width=2, frame_rate=22050, channels=1
                    )
                return AudioSegment.from_file(buffer, format=fmt)
            except Exception:
                continue
        raise RuntimeError("Could not decode audio bytes in any supported format.")

    @staticmethod
    def _adjust_rate(audio: AudioSegment, rate: float) -> AudioSegment:
        """
        Adjust playback speed without changing pitch (time-stretching).

        For simplicity, uses frame-rate manipulation which slightly
        shifts pitch. For production, consider pyrubberband.

        A rate < 1.0 makes speech SLOWER (elderly-friendly).
        A rate > 1.0 makes speech FASTER.
        """
        # Change frame rate then convert back → changes speed + pitch slightly
        new_frame_rate = int(audio.frame_rate * rate)
        adjusted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
        # Restore standard frame rate for correct playback
        adjusted = adjusted.set_frame_rate(audio.frame_rate)
        return adjusted

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_and_clean(text: str) -> str:
        """Validate input text and ensure proper UTF-8 Malayalam encoding."""
        if not isinstance(text, str):
            raise ValueError(f"Expected str, got {type(text).__name__}")

        # Ensure proper UTF-8 encoding round-trip
        text = text.encode("utf-8").decode("utf-8").strip()

        if not text:
            raise ValueError("Text must not be empty.")

        # Log Unicode range check (Malayalam block: U+0D00–U+0D7F)
        malayalam_chars = sum(1 for c in text if "\u0D00" <= c <= "\u0D7F")
        total_chars = sum(1 for c in text if not c.isspace())
        if total_chars > 0:
            ratio = malayalam_chars / total_chars
            if ratio < 0.3:
                logger.warning(
                    "Low Malayalam character ratio (%.0f%%). "
                    "Input may not be Malayalam: '%s...'",
                    ratio * 100,
                    text[:40],
                )

        return text

    def _format_from_path(self, path: str) -> str:
        """Infer audio format from file extension, defaulting to instance setting."""
        ext = Path(path).suffix.lower().strip(".")
        if ext in ("mp3", "wav", "ogg", "flac"):
            return ext
        return self.default_format

    @staticmethod
    def _clamp_rate(rate: float) -> float:
        """Clamp speaking rate to safe bounds."""
        clamped = max(MalayalamSynthesizer._MIN_RATE, min(rate, MalayalamSynthesizer._MAX_RATE))
        if clamped != rate:
            logger.warning("Speaking rate %.2f clamped to %.2f", rate, clamped)
        return clamped
