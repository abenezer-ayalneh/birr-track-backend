"""OCR API routes."""

from __future__ import annotations

import logging
from time import perf_counter

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.response_models import ErrorResponse, OCRLineResponse, OCRResponse
from app.services.ocr_service import OCRServiceError, get_ocr_service
from app.services.preprocessing import ImageProcessingError, decode_image, prepare_image_for_paddle_ocr

LOGGER_NAME = "ocr_microservice.routes.ocr"
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="", tags=["ocr"])
logger = logging.getLogger(LOGGER_NAME)


@router.post(
    "/ocr",
    response_model=OCRResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    },
)
async def ocr_extract(file: UploadFile = File(...)) -> OCRResponse:
    """Extract OCR text from an uploaded receipt image."""
    started_at = perf_counter()
    logger.info("OCR request received filename=%s content_type=%s", file.filename, file.content_type)

    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload: only image files are supported.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload: file is empty.",
        )
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file is too large. Maximum allowed size is 10MB.",
        )

    try:
        image = decode_image(file_bytes)
        prepared = prepare_image_for_paddle_ocr(image)
        result = get_ocr_service().extract_text(prepared)
    except ImageProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except OCRServiceError as exc:
        logger.exception("OCR extraction failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OCR processing failed.",
        ) from exc
    finally:
        await file.close()

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info("OCR request completed in %.2f ms", elapsed_ms)
    return OCRResponse(
        text=result.text,
        lines=[
            OCRLineResponse(text=line.text, confidence=line.confidence)
            for line in result.lines
        ],
    )
