"""API request models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMExtractRequest(BaseModel):
    """Request body for transaction extraction from OCR text."""

    text: str = Field(
        ...,
        min_length=1,
        description="Raw OCR text to extract structured transaction fields from.",
    )
