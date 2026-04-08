"""FastAPI application entrypoint for OCR microservice."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routes.llm import router as llm_router
from app.routes.ocr import router as ocr_router
from app.services.ocr_service import get_ocr_service

LOGGER_NAME = "ocr_microservice"


def configure_logging() -> None:
    """Configure baseline structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Preload OCR model once during startup.

    LLM is loaded lazily on first /llm/extract call so Docker/OCR-only deploys work
    without a mounted .gguf file.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.info("Starting OCR microservice and warming OCR engine")
    get_ocr_service()
    logger.info("OCR engine ready (LLM loads on first use if model file exists)")
    yield
    logger.info("Stopping OCR microservice")


configure_logging()
app = FastAPI(
    title="OCR Microservice",
    version="1.0.0",
    description="CPU-optimized OCR+LLM microservice for receipt data extraction.",
    lifespan=lifespan,
)
app.include_router(ocr_router)
app.include_router(llm_router)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Normalize framework validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Invalid request payload: {exc.errors()}"},
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Prevent server crashes and return safe generic error payload."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.exception("Unhandled server error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Basic liveness endpoint."""
    return {"status": "ok"}
