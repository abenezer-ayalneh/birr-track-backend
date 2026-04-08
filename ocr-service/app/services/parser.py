"""Defensive parsing and normalization for LLM extraction output."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

EXPECTED_FIELDS = ("bank_name", "amount", "transaction_id", "timestamp")

DEFAULT_CONFIDENCE_PARSE_FAILURE = 0.5
CONFIDENCE_ALL_FIELDS_PRESENT = 0.85
CONFIDENCE_ONE_FIELD_MISSING = 0.75
CONFIDENCE_MULTIPLE_FIELDS_MISSING = 0.6

TIMESTAMP_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
)


def build_fallback_payload() -> dict[str, str | float | None]:
    """Return safe response when parsing fails."""
    return {
        "bank_name": None,
        "amount": None,
        "transaction_id": None,
        "timestamp": None,
        "confidence": DEFAULT_CONFIDENCE_PARSE_FAILURE,
    }


def parse_extraction_output(raw_output: str) -> dict[str, str | float | None]:
    """
    Parse model output into the extraction response shape.

    Raises:
        ValueError: When no valid JSON object can be parsed.
    """
    parsed_json = _extract_json_dict(raw_output)
    normalized = _normalize_fields(parsed_json)
    normalized["confidence"] = _compute_confidence(normalized)
    return normalized


def _extract_json_dict(raw_output: str) -> dict[str, Any]:
    if not raw_output.strip():
        raise ValueError("LLM output is empty.")

    # First try direct parsing for ideal model behavior.
    try:
        value = json.loads(raw_output)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    cleaned_output = raw_output.strip().replace("```json", "").replace("```", "").strip()
    if cleaned_output:
        try:
            value = json.loads(cleaned_output)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass

    # Fallback: locate the first balanced JSON object from free-form text.
    candidate = _find_balanced_json_object(raw_output)
    if candidate is None:
        raise ValueError("No JSON object found in LLM output.")

    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("Parsed LLM output is not a JSON object.")
    return value


def _find_balanced_json_object(raw_output: str) -> str | None:
    start_index = raw_output.find("{")
    if start_index == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for index in range(start_index, len(raw_output)):
        char = raw_output[index]
        if escape_next:
            escape_next = False
            continue
        if char == "\\" and in_string:
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw_output[start_index : index + 1]
    return None


def _normalize_fields(payload: dict[str, Any]) -> dict[str, str | float | None]:
    bank_name = _normalize_string(payload.get("bank_name"))
    transaction_id = _normalize_string(payload.get("transaction_id"))
    amount = _normalize_amount(payload.get("amount"))
    timestamp = _normalize_timestamp(payload.get("timestamp"))
    return {
        "bank_name": bank_name,
        "amount": amount,
        "transaction_id": transaction_id,
        "timestamp": timestamp,
    }


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_amount(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    raw_text = str(value).strip()
    if not raw_text:
        return None

    # Keep digits, decimal separators, and minus signs; normalize commas.
    candidate = re.sub(r"[^\d,.\-]", "", raw_text)
    if not candidate:
        return None

    if candidate.count(",") > 0 and candidate.count(".") == 0:
        candidate = candidate.replace(",", ".")
    else:
        candidate = candidate.replace(",", "")

    try:
        return float(candidate)
    except ValueError:
        return None


def _normalize_timestamp(value: Any) -> str | None:
    text = _normalize_string(value)
    if text is None:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).isoformat()
    except ValueError:
        pass

    for pattern in TIMESTAMP_FORMATS:
        try:
            parsed = datetime.strptime(text, pattern)
            return parsed.isoformat()
        except ValueError:
            continue
    return None


def _compute_confidence(normalized: dict[str, str | float | None]) -> float:
    missing_fields = sum(1 for field in EXPECTED_FIELDS if normalized.get(field) is None)
    if missing_fields == 0:
        return CONFIDENCE_ALL_FIELDS_PRESENT
    if missing_fields == 1:
        return CONFIDENCE_ONE_FIELD_MISSING
    return CONFIDENCE_MULTIPLE_FIELDS_MISSING
