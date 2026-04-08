"""LLM API routes."""

from __future__ import annotations

import logging
from time import perf_counter

from fastapi import APIRouter, status

from app.models.request_models import LLMExtractRequest
from app.models.response_models import ErrorResponse, LLMExtractResponse
from app.services.llm_service import LLMModelNotFoundError, LLMServiceError, get_llm_service
from app.services.parser import build_fallback_payload

router = APIRouter(prefix="/llm", tags=["llm"])
logger = logging.getLogger("ocr_microservice.routes.llm")


@router.get("/health")
async def llm_health_check() -> dict[str, str]:
    """Basic liveness endpoint for LLM route group."""
    return {"status": "ok"}


@router.post(
    "/extract",
    response_model=LLMExtractResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    },
)
async def llm_extract(payload: LLMExtractRequest) -> LLMExtractResponse:
    """Extract structured transaction data from OCR text via local LLM."""
    started_at = perf_counter()
    logger.info("LLM extract request received")

    try:
        extracted = get_llm_service().extract_transaction_data(payload.text)
    except LLMModelNotFoundError as exc:
        logger.warning("LLM skipped (no model file): %s", exc)
        extracted = build_fallback_payload()
    except LLMServiceError:
        logger.exception("LLM inference failed; using fallback payload")
        extracted = build_fallback_payload()
    except Exception:
        logger.exception("Unexpected LLM route failure; using fallback payload")
        extracted = build_fallback_payload()

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info("LLM extract request completed in %.2f ms", elapsed_ms)
    return LLMExtractResponse(**extracted)
