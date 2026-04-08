"""Global LLM service backed by llama-cpp-python."""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from llama_cpp import Llama

from app.services.parser import build_fallback_payload, parse_extraction_output
from app.services.prompt_builder import build_extraction_prompt

LOGGER_NAME = "ocr_microservice.llm_service"

# Dedicated constants to avoid magic values in model configuration.
DEFAULT_MODEL_PATH = "models/mistral-7b-instruct.gguf"
DEFAULT_CONTEXT_WINDOW = 2048
DEFAULT_CPU_THREADS = 8
DEFAULT_GPU_LAYERS = 0
DEFAULT_MAX_TOKENS = 300
DEFAULT_TEMPERATURE = 0.1

_SERVICE_INSTANCE: "LLMService | None" = None
_SERVICE_LOCK = threading.Lock()


class LLMServiceError(RuntimeError):
    """Raised when LLM inference fails unexpectedly."""


class LLMModelNotFoundError(LLMServiceError):
    """Raised when LLM_MODEL_PATH points to a file that does not exist."""


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Runtime configuration for the local LLM."""

    model_path: str = DEFAULT_MODEL_PATH
    n_ctx: int = DEFAULT_CONTEXT_WINDOW
    n_threads: int = DEFAULT_CPU_THREADS
    n_gpu_layers: int = DEFAULT_GPU_LAYERS
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE

    @staticmethod
    def from_env() -> "LLMConfig":
        """Build config from environment variables with safe fallbacks."""
        return LLMConfig(
            model_path=os.getenv("LLM_MODEL_PATH", DEFAULT_MODEL_PATH),
            n_ctx=_safe_int_env("LLM_N_CTX", DEFAULT_CONTEXT_WINDOW),
            n_threads=_safe_int_env("LLM_N_THREADS", DEFAULT_CPU_THREADS),
            n_gpu_layers=_safe_int_env("LLM_N_GPU_LAYERS", DEFAULT_GPU_LAYERS),
            max_tokens=_safe_int_env("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS),
            temperature=_safe_float_env("LLM_TEMPERATURE", DEFAULT_TEMPERATURE),
        )


class LLMService:
    """Wrapper around llama.cpp inference with a single loaded model."""

    def __init__(self, config: LLMConfig) -> None:
        self._logger = logging.getLogger(LOGGER_NAME)
        self._config = config
        self._logger.info(
            "Initializing local LLM model_path=%s n_ctx=%d n_threads=%d n_gpu_layers=%d",
            config.model_path,
            config.n_ctx,
            config.n_threads,
            config.n_gpu_layers,
        )
        started_at = perf_counter()
        self._llm = Llama(
            model_path=config.model_path,
            n_ctx=config.n_ctx,
            n_threads=config.n_threads,
            n_gpu_layers=config.n_gpu_layers,
            verbose=False,
        )
        elapsed_ms = (perf_counter() - started_at) * 1000
        self._logger.info("Local LLM initialized in %.2f ms", elapsed_ms)

    def infer(self, prompt: str, *, max_tokens: int | None = None, temperature: float | None = None) -> str:
        """Run deterministic text generation and return raw model output text."""
        if not prompt.strip():
            raise LLMServiceError("Prompt cannot be empty.")

        resolved_max_tokens = max_tokens if max_tokens is not None else self._config.max_tokens
        resolved_temperature = temperature if temperature is not None else self._config.temperature

        started_at = perf_counter()
        try:
            result: dict[str, Any] = self._llm(
                prompt,
                max_tokens=resolved_max_tokens,
                temperature=resolved_temperature,
            )
        except Exception as exc:  # noqa: BLE001 - external inference exceptions
            raise LLMServiceError("Local LLM inference failed.") from exc

        elapsed_ms = (perf_counter() - started_at) * 1000
        self._logger.info("LLM inference completed in %.2f ms", elapsed_ms)

        choices = result.get("choices", [])
        if not choices:
            raise LLMServiceError("Local LLM produced an empty response.")

        generated_text = str(choices[0].get("text", "")).strip()
        if not generated_text:
            raise LLMServiceError("Local LLM response text is empty.")
        return generated_text

    def extract_transaction_data(self, ocr_text: str) -> dict[str, str | float | None]:
        """Extract transaction fields with safe parsing and fallback response."""
        prompt = build_extraction_prompt(ocr_text=ocr_text)
        raw_output = self.infer(prompt=prompt)
        try:
            parsed_output = parse_extraction_output(raw_output)
            self._logger.info("LLM output parsing succeeded")
            return parsed_output
        except (ValueError, TypeError, KeyError):
            self._logger.warning("LLM output parsing failed; using fallback payload")
            return build_fallback_payload()


def get_llm_service() -> LLMService:
    """Return singleton LLM service instance, loading on first successful access."""
    global _SERVICE_INSTANCE
    if _SERVICE_INSTANCE is not None:
        return _SERVICE_INSTANCE
    with _SERVICE_LOCK:
        if _SERVICE_INSTANCE is not None:
            return _SERVICE_INSTANCE
        config = LLMConfig.from_env()
        if not os.path.isfile(config.model_path):
            raise LLMModelNotFoundError(
                f"LLM model file not found: {config.model_path}. "
                "Set LLM_MODEL_PATH or mount a .gguf into the container."
            )
        _SERVICE_INSTANCE = LLMService(config=config)
        return _SERVICE_INSTANCE


def _safe_int_env(name: str, default: int) -> int:
    """Parse integer environment value with fallback."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _safe_float_env(name: str, default: float) -> float:
    """Parse float environment value with fallback."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default
