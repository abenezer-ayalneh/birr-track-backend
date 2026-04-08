"""Core OCR service with globally initialized PaddleOCR engine."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from time import perf_counter
import numpy as np
from paddleocr import PaddleOCR

from app.services.ocr_result_normalize import normalize_paddle_ocr_raw

LOGGER_NAME = "ocr_microservice.ocr_service"
DEFAULT_LANGUAGE = "en"

_SERVICE_INSTANCE: "OCRService | None" = None
_SERVICE_LOCK = threading.Lock()


class OCRServiceError(RuntimeError):
    """Raised when OCR extraction fails unexpectedly."""


@dataclass(slots=True)
class OCRLine:
    """Single OCR text line with confidence score."""

    text: str
    confidence: float


@dataclass(slots=True)
class OCRResult:
    """Structured OCR result returned by the service."""

    text: str
    lines: list[OCRLine]


class OCRService:
    """Encapsulates PaddleOCR usage and output normalization."""

    def __init__(self, language: str = DEFAULT_LANGUAGE) -> None:
        self._logger = logging.getLogger(LOGGER_NAME)
        self._logger.info("Initializing PaddleOCR model (lang=%s)", language)
        ocr_init_args = {
            "use_angle_cls": True,
            "lang": language,
            "use_gpu": False,
            "show_log": False,
        }
        # PaddleOCR's constructor args vary across versions. Retry by dropping only
        # explicitly unsupported keys reported by the library.
        while True:
            try:
                self._ocr = PaddleOCR(**ocr_init_args)
                break
            except ValueError as exc:
                match = re.search(r"Unknown argument: ([A-Za-z_][A-Za-z0-9_]*)", str(exc))
                if not match:
                    raise
                unsupported_arg = match.group(1)
                if unsupported_arg not in ocr_init_args:
                    raise
                self._logger.warning("PaddleOCR does not support '%s'; retrying without it", unsupported_arg)
                ocr_init_args.pop(unsupported_arg, None)
        self._logger.info("PaddleOCR initialization completed")

    def extract_text(self, image: np.ndarray) -> OCRResult:
        """
        Extract text lines from a preprocessed image.

        Args:
            image: OpenCV image array.

        Returns:
            OCRResult with concatenated text and per-line confidence.
        """
        if image is None or not isinstance(image, np.ndarray):
            raise OCRServiceError("Invalid image input. Expected a NumPy array.")
        if image.size == 0:
            raise OCRServiceError("Invalid image input. Empty image array received.")

        started_at = perf_counter()
        try:
            # PaddleOCR 3.x uses predict(); ocr() delegates to it. Output shape differs from 2.x (see _normalize_output).
            predict_fn = getattr(self._ocr, "predict", None)
            raw_output = predict_fn(image) if callable(predict_fn) else self._ocr.ocr(image)
        except Exception as exc:  # noqa: BLE001 - external OCR library exception surface
            raise OCRServiceError("OCR engine failed to process image.") from exc

        tuples = normalize_paddle_ocr_raw(raw_output)
        ocr_lines = [OCRLine(text=t, confidence=c) for t, c in tuples]
        combined_text = "\n".join(t for t, _ in tuples)
        result = OCRResult(text=combined_text, lines=ocr_lines)
        elapsed_ms = (perf_counter() - started_at) * 1000
        self._logger.info("OCR extraction completed in %.2f ms", elapsed_ms)
        return result


def get_ocr_service() -> OCRService:
    """Return singleton OCR service instance."""
    global _SERVICE_INSTANCE

    if _SERVICE_INSTANCE is None:
        with _SERVICE_LOCK:
            if _SERVICE_INSTANCE is None:
                _SERVICE_INSTANCE = OCRService(language=DEFAULT_LANGUAGE)
    return _SERVICE_INSTANCE
