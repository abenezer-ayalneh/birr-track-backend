"""API response models for OCR endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OCRLineResponse(BaseModel):
    """Structured single OCR line."""

    text: str = Field(description="Extracted line text")
    confidence: float = Field(description="OCR confidence score for this line")


class OCRResponse(BaseModel):
    """Final OCR response contract."""

    text: str = Field(description="Full extracted text concatenated by line breaks")
    lines: list[OCRLineResponse] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standard API error response payload."""

    detail: str


class LLMExtractResponse(BaseModel):
    """Structured transaction fields extracted from OCR text."""

    bank_name: str | None = Field(default=None)
    amount: float | None = Field(default=None)
    transaction_id: str | None = Field(default=None)
    timestamp: str | None = Field(default=None, description="ISO formatted timestamp when available")
    confidence: float = Field(ge=0.0, le=1.0)
