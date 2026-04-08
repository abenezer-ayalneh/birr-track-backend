"""Prompt builders for local LLM extraction."""

from __future__ import annotations

SYSTEM_PROMPT = """You are an information extraction system.

Extract the following fields from the text:

- bank_name
- amount (number only)
- transaction_id
- timestamp (ISO format if possible)

Rules:
- Do not guess values
- If a field is missing, return null
- Return ONLY valid JSON
"""


def build_extraction_prompt(ocr_text: str) -> str:
    """Create deterministic extraction prompt for receipt text."""
    sanitized_text = ocr_text.strip()
    return f"""{SYSTEM_PROMPT}

OCR Text:
{sanitized_text}
"""
