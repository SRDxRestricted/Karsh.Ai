"""
OfflineAgriBrain — Local Agricultural AI for Kerala Farmers
=============================================================
Runs a quantized GGUF model (Phi-3-mini, Gemma-2B, etc.) entirely
offline using llama-cpp-python. Zero network calls.
"""

import os
import sys
import glob
import logging
from typing import Optional

from llama_cpp import Llama

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class OfflineAgriBrain:
    """
    Offline agricultural query engine powered by a local GGUF model.

    Args:
        model_path:     Path to the .gguf model file, OR a directory
                        containing exactly one .gguf file.
        n_ctx:          Context window size (tokens). 2048 is sufficient
                        for short Q&A exchanges.
        n_gpu_layers:   Number of layers to offload to GPU.
                        0 = pure CPU, -1 = offload all layers.
        n_threads:      CPU threads for inference. Defaults to
                        half the available cores.
        seed:           RNG seed for reproducibility. -1 = random.
        verbose:        If False, suppresses llama.cpp internal logs.
    """

    _SYSTEM_PROMPT = (
        "You are an offline agricultural expert in Kerala. "
        "You specialise in coconut, rubber, spice, rice, and banana cultivation. "
        "Answer the farmer's question accurately and practically. "
        "Keep responses under 50 words. "
        "If the question is in Malayalam, respond in Malayalam. "
        "If the question is in English, respond in English."
    )

    def __init__(
        self,
        model_path: str = "models",
        n_ctx: int = 2048,
        n_gpu_layers: int = 0,
        n_threads: Optional[int] = None,
        seed: int = 42,
        verbose: bool = False,
    ) -> None:
        self._model_file = self._resolve_model_path(model_path)
        self._n_ctx = n_ctx

        if n_threads is None:
            n_threads = max(1, (os.cpu_count() or 4) // 2)

        logger.info("Loading GGUF model: %s", self._model_file)
        logger.info(
            "Config: ctx=%d, gpu_layers=%d, threads=%d, seed=%d",
            n_ctx, n_gpu_layers, n_threads, seed,
        )

        self._llm = Llama(
            model_path=self._model_file,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_threads=n_threads,
            seed=seed,
            verbose=verbose,
        )

        logger.info("Model loaded successfully.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_agri_query(self, malayalam_text: str) -> str:
        """
        Process a farmer's agricultural query and return an expert response.

        Args:
            malayalam_text: The farmer's question (Malayalam or English).

        Returns:
            A concise agricultural response (≤50 words).

        Raises:
            ValueError:  If the input is empty.
            RuntimeError: If inference fails.
        """
        if not isinstance(malayalam_text, str):
            raise ValueError(f"Expected str, got {type(malayalam_text).__name__}")

        malayalam_text = malayalam_text.strip()
        if not malayalam_text:
            raise ValueError("Query text must not be empty.")

        prompt = self._build_prompt(malayalam_text)
        logger.info("Query: %s", malayalam_text[:80])

        try:
            output = self._llm(
                prompt,
                max_tokens=150,          # ~50 words ≈ 100–150 tokens
                temperature=0.3,         # low temp for factual answers
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                stop=["<|end|>", "<|user|>", "\nUser:", "\nFarmer:"],
            )

            response = output["choices"][0]["text"].strip()

            # Clean up any leftover prompt artifacts
            response = self._clean_response(response)

            logger.info("Response: %s", response[:80])
            return response

        except Exception as exc:
            logger.error("Inference failed: %s", exc, exc_info=True)
            raise RuntimeError(f"Model inference failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Prompt Construction
    # ------------------------------------------------------------------

    def _build_prompt(self, user_query: str) -> str:
        """
        Build a chat-style prompt compatible with common GGUF model
        formats (Phi-3, Gemma, ChatML, Alpaca).

        Uses the ChatML template as it is widely supported.
        """
        prompt = (
            "<|system|>\n"
            f"{self._SYSTEM_PROMPT}\n"
            "<|end|>\n"
            "<|user|>\n"
            f"{user_query}\n"
            "<|end|>\n"
            "<|assistant|>\n"
        )
        return prompt

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_model_path(path: str) -> str:
        """
        Resolve the model path.

        If ``path`` is a file, use it directly.
        If ``path`` is a directory, find the first .gguf file inside.
        """
        path = os.path.abspath(path)

        if os.path.isfile(path):
            if not path.lower().endswith(".gguf"):
                logger.warning("Model file does not have .gguf extension: %s", path)
            return path

        if os.path.isdir(path):
            gguf_files = sorted(glob.glob(os.path.join(path, "*.gguf")))
            if not gguf_files:
                logger.error("No .gguf files found in directory: %s", path)
                sys.exit(1)
            if len(gguf_files) > 1:
                logger.warning(
                    "Multiple .gguf files found, using first: %s", gguf_files[0]
                )
            return gguf_files[0]

        logger.error("Model path does not exist: %s", path)
        sys.exit(1)

    @staticmethod
    def _clean_response(text: str) -> str:
        """Strip common template artifacts from model output."""
        for tag in ("<|end|>", "<|assistant|>", "<|user|>", "<|system|>"):
            text = text.replace(tag, "")

        # Remove any trailing incomplete sentence fragment
        lines = text.strip().splitlines()
        cleaned = "\n".join(line.strip() for line in lines if line.strip())
        return cleaned
