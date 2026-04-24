"""
VoicePipeline — Full-duplex Malayalam Voice Assistant Pipeline
===============================================================
Integrates:
    - Live microphone capture (sounddevice)
    - Silence-based utterance detection
    - Malayalam ASR  (malayalam_asr.transcribe_malayalam)
    - Query processing (pluggable placeholder)
    - Malayalam TTS  (malayalam_tts.MalayalamSynthesizer)
    - Echo-cancellation-aware playback

Audio flow:
    Mic → silence detect → save segment → ASR → process_query → TTS → speaker
    (mic is muted during TTS playback to prevent feedback loop)
"""

import os
import sys
import wave
import time
import queue
import tempfile
import logging
import threading
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from malayalam_asr import transcribe_malayalam
from malayalam_tts import MalayalamSynthesizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("VoicePipeline")


# ---------------------------------------------------------------------------
# AgriBrain Query Processor
# ---------------------------------------------------------------------------
try:
    from offline_agri_brain import OfflineAgriBrain
    # Attempt to initialize the brain (will fail if models directory is missing or empty)
    _brain = OfflineAgriBrain(model_path="models", n_ctx=2048, verbose=False)
    
    def process_query(text: str) -> str:
        """Process transcribed text using the offline LLM."""
        logger.info("process_query received: %s", text)
        return _brain.process_agri_query(text)
        
except Exception as e:
    logger.warning("OfflineAgriBrain could not be loaded: %s. Using dummy processor.", e)
    
    def process_query(text: str) -> str:
        """Placeholder: accepts transcribed Malayalam text and returns a response."""
        logger.info("process_query (dummy) received: %s", text)
        return (
            f"നിങ്ങളുടെ ചോദ്യം ലഭിച്ചു: \"{text}\". "
            "ഉത്തരം ഉടൻ ലഭ്യമാക്കാം."
        )

# ---------------------------------------------------------------------------
# VoicePipeline
# ---------------------------------------------------------------------------

class VoicePipeline:
    """
    Continuous voice assistant pipeline with echo cancellation.

    Parameters
    ----------
    query_handler : callable, optional
        Function(str) -> str that processes transcribed text and returns
        a response. Defaults to the dummy ``process_query``.
    speaking_rate : float
        TTS playback speed. 0.75 = slower (elderly-friendly), 1.0 = normal.
    sample_rate : int
        Microphone sample rate in Hz.
    channels : int
        Number of audio channels (1 = mono).
    dtype : str
        NumPy dtype for audio samples.
    block_duration_ms : int
        Duration of each audio block read from the mic (milliseconds).
    silence_threshold : float
        RMS amplitude below which audio is considered silence.
        Tune this for your environment (farm ambient noise).
    silence_duration : float
        Seconds of continuous silence required to finalise an utterance.
    min_utterance_duration : float
        Minimum seconds of speech before an utterance is accepted
        (filters out coughs, clicks, etc.).
    max_utterance_duration : float
        Maximum seconds before force-stopping a recording.
    pre_speech_buffer_ms : int
        Milliseconds of audio to keep *before* speech onset
        (avoids clipping the first syllable).
    """

    def __init__(
        self,
        query_handler: Optional[Callable[[str], str]] = None,
        speaking_rate: float = 1.0,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "int16",
        block_duration_ms: int = 30,
        silence_threshold: float = 300.0,
        silence_duration: float = 1.5,
        min_utterance_duration: float = 0.6,
        max_utterance_duration: float = 30.0,
        pre_speech_buffer_ms: int = 300,
    ) -> None:

        self.query_handler = query_handler or process_query
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.block_duration_ms = block_duration_ms
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_utterance_duration = min_utterance_duration
        self.max_utterance_duration = max_utterance_duration
        self.pre_speech_buffer_ms = pre_speech_buffer_ms

        # Derived
        self._block_size = int(sample_rate * block_duration_ms / 1000)
        self._pre_speech_blocks = max(1, int(pre_speech_buffer_ms / block_duration_ms))

        # TTS engine
        self._tts = MalayalamSynthesizer(speaking_rate=speaking_rate)

        # Echo-cancellation state
        self._is_playing = threading.Event()   # SET while TTS audio is playing
        self._stop_event = threading.Event()   # SET to shut down the pipeline

        # Audio queue for mic callback → processing thread
        self._audio_queue: queue.Queue[Optional[np.ndarray]] = queue.Queue()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Start the voice pipeline (blocking).

        Runs continuously until interrupted with Ctrl+C or ``stop()``
        is called from another thread.
        """
        self._stop_event.clear()
        logger.info("=" * 60)
        logger.info("  കൃഷിമിത്രം Voice Pipeline — Starting")
        logger.info("  Silence threshold : %.0f", self.silence_threshold)
        logger.info("  Silence duration  : %.1fs", self.silence_duration)
        logger.info("  Sample rate       : %d Hz", self.sample_rate)
        logger.info("=" * 60)
        logger.info("🎙️  മലയാളത്തിൽ സംസാരിക്കൂ... (Speak in Malayalam...)")

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self._block_size,
                callback=self._audio_callback,
            ):
                self._processing_loop()
        except KeyboardInterrupt:
            logger.info("Pipeline interrupted by user.")
        except Exception as exc:
            logger.error("Pipeline error: %s", exc, exc_info=True)
        finally:
            self._stop_event.set()
            logger.info("Pipeline stopped.")

    def stop(self) -> None:
        """Signal the pipeline to stop gracefully."""
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Microphone Callback (runs in a separate PortAudio thread)
    # ------------------------------------------------------------------

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """
        Called by sounddevice for each audio block.

        ECHO CANCELLATION: If TTS is currently playing (``_is_playing``
        is set), we discard the mic input entirely. This prevents the
        speaker output from being captured by the mic and re-processed,
        which would cause infinite feedback loops.
        """
        if status:
            logger.debug("Audio callback status: %s", status)

        # --- Echo gate ---
        if self._is_playing.is_set():
            return  # Discard mic data while speaker is active

        # Enqueue a copy (indata buffer is reused by PortAudio)
        self._audio_queue.put(indata.copy())

    # ------------------------------------------------------------------
    # Main Processing Loop
    # ------------------------------------------------------------------

    def _processing_loop(self) -> None:
        """
        Continuously reads audio blocks from the queue, detects speech
        utterances via silence detection, and dispatches them for
        transcription → query → TTS.
        """
        ring_buffer: list[np.ndarray] = []  # pre-speech ring buffer
        utterance_blocks: list[np.ndarray] = []
        is_speaking = False
        silence_blocks = 0
        silence_blocks_needed = int(self.silence_duration * 1000 / self.block_duration_ms)
        max_blocks = int(self.max_utterance_duration * 1000 / self.block_duration_ms)

        while not self._stop_event.is_set():
            try:
                block = self._audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if block is None:
                break

            rms = self._rms(block)

            if not is_speaking:
                # Maintain a rolling pre-speech buffer
                ring_buffer.append(block)
                if len(ring_buffer) > self._pre_speech_blocks:
                    ring_buffer.pop(0)

                if rms > self.silence_threshold:
                    # Speech onset detected
                    is_speaking = True
                    silence_blocks = 0
                    # Prepend the ring buffer so we don't clip the first syllable
                    utterance_blocks = list(ring_buffer)
                    utterance_blocks.append(block)
                    ring_buffer.clear()
                    logger.info("🔴 Speech detected (RMS=%.0f)", rms)
            else:
                utterance_blocks.append(block)

                if rms < self.silence_threshold:
                    silence_blocks += 1
                else:
                    silence_blocks = 0

                # Check termination conditions
                force_stop = len(utterance_blocks) >= max_blocks
                silence_stop = silence_blocks >= silence_blocks_needed

                if silence_stop or force_stop:
                    duration = len(utterance_blocks) * self.block_duration_ms / 1000
                    reason = "silence" if silence_stop else "max duration"
                    logger.info(
                        "⏹️  Utterance ended (%s), duration=%.1fs", reason, duration
                    )

                    if duration >= self.min_utterance_duration:
                        audio_data = np.concatenate(utterance_blocks, axis=0)
                        # Process in current thread (keeps pipeline sequential
                        # so playback finishes before next listen)
                        self._handle_utterance(audio_data)
                        logger.info("🎙️  Listening again...")
                    else:
                        logger.debug(
                            "Utterance too short (%.1fs), discarding.", duration
                        )

                    # Reset state
                    utterance_blocks.clear()
                    ring_buffer.clear()
                    is_speaking = False
                    silence_blocks = 0

    # ------------------------------------------------------------------
    # Utterance Handler (ASR → Query → TTS)
    # ------------------------------------------------------------------

    def _handle_utterance(self, audio_data: np.ndarray) -> None:
        """
        Full pipeline for a single utterance:
            1. Save raw audio to temp WAV
            2. Transcribe via ASR
            3. Pass text to query handler
            4. Synthesise response via TTS
            5. Play back with echo gate active
        """
        wav_path = self._save_wav(audio_data)
        try:
            # --- Step 1: ASR ---
            logger.info("📝 Transcribing...")
            transcript = transcribe_malayalam(wav_path)
            if not transcript:
                logger.warning("Empty transcription, skipping.")
                return
            logger.info("📝 Transcript: %s", transcript)

            # --- Step 2: Query Processing ---
            logger.info("🤔 Processing query...")
            response = self.query_handler(transcript)
            if not response:
                logger.warning("Empty response from query handler, skipping.")
                return
            logger.info("💬 Response: %s", response)

            # --- Step 3: TTS ---
            tts_path = tempfile.mktemp(suffix=".mp3", prefix="krishi_tts_")
            self._tts.speak(response, tts_path)

            # --- Step 4: Playback with echo gate ---
            self._play_audio(tts_path)

        except Exception as exc:
            logger.error("Utterance handling failed: %s", exc, exc_info=True)
        finally:
            # Clean up temp WAV
            self._safe_delete(wav_path)

    # ------------------------------------------------------------------
    # Audio Playback with Echo Cancellation
    # ------------------------------------------------------------------

    def _play_audio(self, audio_path: str) -> None:
        """
        Play an audio file through the speakers.

        ECHO CANCELLATION:
        - Sets ``_is_playing`` BEFORE playback starts.
        - Clears it AFTER playback completes + a brief cooldown.
        - The mic callback checks this flag and discards input
          while it is set, preventing feedback loops.
        """
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(audio_path)
            # Convert to numpy array for sounddevice
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
            else:
                samples = samples.reshape((-1, 1))
            # Normalize to [-1, 1]
            max_val = float(2 ** (audio.sample_width * 8 - 1))
            samples = samples / max_val

            logger.info("🔊 Playing response (%0.1fs)...", len(audio) / 1000)

            # --- ECHO GATE ON ---
            self._is_playing.set()
            # Drain any queued mic data captured just before the gate
            self._drain_queue()

            sd.play(samples, samplerate=audio.frame_rate)
            sd.wait()  # Block until playback finishes

            # Brief cooldown: speakers may still resonate for ~200ms
            time.sleep(0.3)

            # Drain anything captured during cooldown
            self._drain_queue()
            # --- ECHO GATE OFF ---
            self._is_playing.clear()

            logger.info("🔊 Playback complete.")
        except Exception as exc:
            logger.error("Playback failed: %s", exc)
            self._is_playing.clear()
        finally:
            self._safe_delete(audio_path)

    def _drain_queue(self) -> None:
        """Discard all pending audio blocks from the mic queue."""
        discarded = 0
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
                discarded += 1
            except queue.Empty:
                break
        if discarded:
            logger.debug("Drained %d stale audio blocks from queue.", discarded)

    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------

    def _save_wav(self, audio_data: np.ndarray) -> str:
        """Save a numpy audio array to a temporary WAV file."""
        tmp = tempfile.NamedTemporaryFile(
            suffix=".wav", prefix="krishi_mic_", delete=False
        )
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())
        logger.debug("Saved mic audio: %s (%d samples)", tmp.name, len(audio_data))
        return tmp.name

    @staticmethod
    def _rms(block: np.ndarray) -> float:
        """Compute root-mean-square amplitude of an audio block."""
        return float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))

    @staticmethod
    def _safe_delete(path: str) -> None:
        """Delete a file if it exists, silently ignoring errors."""
        try:
            if path and os.path.isfile(path):
                os.unlink(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="കൃഷിമിത്രം Voice Pipeline — Malayalam Voice AI for Farmers"
    )
    parser.add_argument(
        "--rate", type=float, default=0.85,
        help="TTS speaking rate (0.5–2.0). Default 0.85 for elderly farmers."
    )
    parser.add_argument(
        "--silence-threshold", type=float, default=300.0,
        help="RMS threshold for silence detection. Increase for noisy environments."
    )
    parser.add_argument(
        "--silence-duration", type=float, default=1.5,
        help="Seconds of silence to end an utterance."
    )
    args = parser.parse_args()

    pipeline = VoicePipeline(
        speaking_rate=args.rate,
        silence_threshold=args.silence_threshold,
        silence_duration=args.silence_duration,
    )
    pipeline.start()
