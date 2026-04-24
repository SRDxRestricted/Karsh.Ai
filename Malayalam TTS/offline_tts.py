"""
Offline Malayalam Text-to-Speech via espeak-ng
===============================================
Zero internet dependency. Uses the locally installed espeak-ng
speech synthesiser with the Malayalam voice (-v ml).
"""

import os
import sys
import shutil
import logging
import subprocess
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults tuned for clarity in noisy rural / farm environments
# ---------------------------------------------------------------------------
_DEFAULT_SPEED = 130       # words-per-minute (espeak default 175 is too fast)
_DEFAULT_PITCH = 50        # 0–99, 50 = normal
_DEFAULT_AMPLITUDE = 150   # 0–200, boosted for outdoor use
_DEFAULT_VOICE = "ml"      # Malayalam
_DEFAULT_GAP = 10          # ms gap between words (adds clarity)


def speak_offline_malayalam(
    text: str,
    speed: int = _DEFAULT_SPEED,
    pitch: int = _DEFAULT_PITCH,
    amplitude: int = _DEFAULT_AMPLITUDE,
    output_file: Optional[str] = None,
) -> Optional[str]:
    """
    Speak Malayalam text offline using espeak-ng.

    Args:
        text:        Malayalam Unicode string (UTF-8).
        speed:       Speaking rate in words-per-minute (80–450).
                     Lower values are clearer for elderly listeners.
        pitch:       Voice pitch (0–99). 50 = normal.
        amplitude:   Volume (0–200). Values above 100 boost output
                     for noisy outdoor environments.
        output_file: If provided, saves audio to this WAV file instead
                     of playing through the speaker. Pass None to play
                     directly.

    Returns:
        The output file path if ``output_file`` was specified, else None.

    Raises:
        FileNotFoundError: If espeak-ng is not installed.
        ValueError:        If text is empty or not a string.
        RuntimeError:      If espeak-ng exits with an error.
    """
    # ------------------------------------------------------------------
    # Validate input
    # ------------------------------------------------------------------
    if not isinstance(text, str):
        raise ValueError(f"Expected str, got {type(text).__name__}")

    text = text.strip()
    if not text:
        raise ValueError("Text must not be empty.")

    # ------------------------------------------------------------------
    # Locate espeak-ng binary
    # ------------------------------------------------------------------
    espeak_bin = _find_espeak()

    # ------------------------------------------------------------------
    # Build command
    # ------------------------------------------------------------------
    cmd = [
        espeak_bin,
        "-v", _DEFAULT_VOICE,       # Malayalam voice
        "-s", str(_clamp(speed, 80, 450)),
        "-p", str(_clamp(pitch, 0, 99)),
        "-a", str(_clamp(amplitude, 0, 200)),
        "-g", str(_DEFAULT_GAP),     # word gap for clarity
    ]

    if output_file:
        output_file = os.path.abspath(output_file)
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        cmd.extend(["-w", output_file])

    # ------------------------------------------------------------------
    # Execute espeak-ng
    #
    # ENCODING NOTE:
    # We pass the Malayalam text via stdin (not as a CLI arg) to avoid
    # shell encoding issues on Windows. stdin is opened in UTF-8 mode
    # explicitly. The text is encoded to UTF-8 bytes before writing to
    # the subprocess pipe.
    # ------------------------------------------------------------------
    cmd.append("--stdin")

    logger.info(
        "espeak-ng: voice=%s speed=%s pitch=%s amp=%s | text='%s...'",
        _DEFAULT_VOICE, speed, pitch, amplitude, text[:40],
    )
    logger.debug("Command: %s", " ".join(cmd))

    try:
        env = os.environ.copy()
        env["LANG"] = "ml_IN.UTF-8"
        env["LC_ALL"] = "ml_IN.UTF-8"

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        text_bytes = text.encode("utf-8")
        stdout, stderr = proc.communicate(input=text_bytes, timeout=30)

        if proc.returncode != 0:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            logger.error("espeak-ng failed (rc=%d): %s", proc.returncode, err_msg)
            raise RuntimeError(f"espeak-ng error (rc={proc.returncode}): {err_msg}")

        if output_file:
            logger.info("Audio saved: %s", output_file)
            return output_file

        logger.info("Playback complete.")
        return None

    except FileNotFoundError:
        raise
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("espeak-ng timed out after 30 seconds.")
    except Exception as exc:
        raise RuntimeError(f"espeak-ng execution failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_espeak() -> str:
    """Locate the espeak-ng binary on the system PATH."""
    binary = shutil.which("espeak-ng")
    if binary:
        return binary

    # Fallback: common install locations on Windows
    if sys.platform == "win32":
        common_paths = [
            r"C:\Program Files\eSpeak NG\espeak-ng.exe",
            r"C:\Program Files (x86)\eSpeak NG\espeak-ng.exe",
        ]
        for p in common_paths:
            if os.path.isfile(p):
                return p

    raise FileNotFoundError(
        "espeak-ng not found. Install it:\n"
        "  Ubuntu/Debian : sudo apt install espeak-ng\n"
        "  Windows       : https://github.com/espeak-ng/espeak-ng/releases\n"
        "  macOS         : brew install espeak-ng"
    )


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp an integer to [lo, hi]."""
    return max(lo, min(value, hi))
