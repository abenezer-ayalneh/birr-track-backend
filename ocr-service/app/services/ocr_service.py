"""Core OCR service with globally initialized PaddleOCR engine."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import numpy as np
from paddleocr import PaddleOCR

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
            # PaddleOCR 3.x: predict() no longer accepts cls=; angle cls is configured via use_angle_cls on init.
            raw_output = self._ocr.ocr(image)
        except Exception as exc:  # noqa: BLE001 - external OCR library exception surface
            raise OCRServiceError("OCR engine failed to process image.") from exc

        result = self._normalize_output(raw_output)
        elapsed_ms = (perf_counter() - started_at) * 1000
        self._logger.info("OCR extraction completed in %.2f ms", elapsed_ms)
        return result

    def _normalize_output(self, raw_output: Any) -> OCRResult:
        """
        Convert PaddleOCR output into a stable service response shape.

        PaddleOCR generally returns nested lists where each detected line is:
        [bbox, (text, confidence)].
        """
        lines: list[OCRLine] = []
        if not raw_output:
            return OCRResult(text="", lines=lines)

        for page in raw_output:
            if not page:
                continue

            for item in page:
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue

                text_payload = item[1]
                if not isinstance(text_payload, (list, tuple)) or len(text_payload) < 2:
                    continue

                text_value = str(text_payload[0]).strip()
                if not text_value:
                    continue

                confidence_value = text_payload[1]
                try:
                    confidence = float(confidence_value)
                except (TypeError, ValueError):
                    confidence = 0.0

                lines.append(OCRLine(text=text_value, confidence=confidence))

        combined_text = "\n".join(line.text for line in lines)
        return OCRResult(text=combined_text, lines=lines)


def get_ocr_service() -> OCRService:
    """Return singleton OCR service instance."""
    global _SERVICE_INSTANCE

    if _SERVICE_INSTANCE is None:
        with _SERVICE_LOCK:
            if _SERVICE_INSTANCE is None:
                _SERVICE_INSTANCE = OCRService(language=DEFAULT_LANGUAGE)
    return _SERVICE_INSTANCE
