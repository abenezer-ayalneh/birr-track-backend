"""Normalize PaddleOCR 2.x and 3.x / PaddleX raw outputs into text lines."""

from __future__ import annotations

from typing import Any

import numpy as np


def normalize_paddle_ocr_raw(raw_output: Any) -> list[tuple[str, float]]:
    """
    Parse PaddleOCR engine output into (text, confidence) lines.

    PaddleOCR 3.x ``predict()`` returns list[dict] with ``res["rec_texts"]`` and
    ``res["rec_scores"]``. PaddleOCR 2.x used nested lists ``[bbox, (text, score)]``.
    """
    if raw_output is None:
        return []

    lines = _lines_from_paddlex_predict(raw_output)
    if not lines:
        lines = _lines_from_legacy_ocr(raw_output)
    return lines


def _lines_from_paddlex_predict(raw_output: Any) -> list[tuple[str, float]]:
    entries: list[Any]
    if isinstance(raw_output, dict):
        entries = [raw_output]
    elif isinstance(raw_output, (list, tuple)):
        entries = list(raw_output)
    else:
        return []

    out: list[tuple[str, float]] = []
    for entry in entries:
        res = _extract_res_dict(entry)
        if res is None:
            continue
        texts = res.get("rec_texts")
        if not texts:
            continue
        scores = res.get("rec_scores")
        flat_scores = np.asarray(scores).ravel() if scores is not None else np.array([])

        for i, raw_text in enumerate(texts):
            text_value = str(raw_text).strip()
            if not text_value:
                continue
            conf = 0.0
            if i < flat_scores.size:
                conf = float(flat_scores[i])
            out.append((text_value, conf))
    return out


def _extract_res_dict(entry: Any) -> dict[str, Any] | None:
    if entry is None:
        return None
    if isinstance(entry, dict):
        inner = entry.get("res")
        if isinstance(inner, dict):
            return inner
        if "rec_texts" in entry:
            return entry
        return None
    json_fn = getattr(entry, "json", None)
    if callable(json_fn):
        try:
            as_dict = json_fn()
        except TypeError:
            as_dict = None
        if isinstance(as_dict, dict):
            return _extract_res_dict(as_dict)
    return None


def _lines_from_legacy_ocr(raw_output: Any) -> list[tuple[str, float]]:
    lines: list[tuple[str, float]] = []
    if not isinstance(raw_output, (list, tuple)):
        return lines

    for page in raw_output:
        if not page or isinstance(page, dict):
            continue
        if not isinstance(page, (list, tuple)):
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

            lines.append((text_value, confidence))

    return lines
