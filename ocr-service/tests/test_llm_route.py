"""Route-level tests for /llm/extract fallback behavior."""

from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes.llm import router as llm_router
    from app.services.llm_service import LLMServiceError

    FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False


class _StubLLMService:
    """Simple test double for the LLM service."""

    def __init__(self, response: dict[str, str | float | None] | None = None, fail: bool = False) -> None:
        self._response = response or {}
        self._fail = fail

    def extract_transaction_data(self, _: str) -> dict[str, str | float | None]:
        if self._fail:
            raise LLMServiceError("inference failed")
        return self._response


class TestLLMRoute(unittest.TestCase):
    """Validate route contract for success and failure paths."""

    @classmethod
    def setUpClass(cls) -> None:
        if not FASTAPI_AVAILABLE:
            raise unittest.SkipTest("fastapi is not installed in this environment")
        app = FastAPI()
        app.include_router(llm_router)
        cls.client = TestClient(app)

    def test_llm_extract_success(self) -> None:
        expected_response = {
            "bank_name": "CBE",
            "amount": 1200.5,
            "transaction_id": "TRX-1",
            "timestamp": "2026-04-02T12:00:00",
            "confidence": 0.85,
        }
        with patch("app.routes.llm.get_llm_service", return_value=_StubLLMService(response=expected_response)):
            response = self.client.post("/llm/extract", json={"text": "raw ocr text"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected_response)

    def test_llm_extract_fallback_on_inference_error(self) -> None:
        with patch("app.routes.llm.get_llm_service", return_value=_StubLLMService(fail=True)):
            response = self.client.post("/llm/extract", json={"text": "raw ocr text"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "bank_name": None,
                "amount": None,
                "transaction_id": None,
                "timestamp": None,
                "confidence": 0.5,
            },
        )


if __name__ == "__main__":
    unittest.main()
