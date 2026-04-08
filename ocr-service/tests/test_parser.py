"""Unit tests for LLM output parser and normalizer."""

from __future__ import annotations

import unittest

from app.services.parser import build_fallback_payload, parse_extraction_output


class TestParser(unittest.TestCase):
    """Parser behavior tests for strict and noisy LLM outputs."""

    def test_parse_valid_json_output(self) -> None:
        raw_output = """
        {
          "bank_name": "Dashen Bank",
          "amount": "1,250.50",
          "transaction_id": "TX-001",
          "timestamp": "2026-04-02 10:15:00"
        }
        """
        result = parse_extraction_output(raw_output)
        self.assertEqual(result["bank_name"], "Dashen Bank")
        self.assertEqual(result["transaction_id"], "TX-001")
        self.assertAlmostEqual(float(result["amount"]), 1250.50)
        self.assertEqual(result["timestamp"], "2026-04-02T10:15:00")
        self.assertEqual(result["confidence"], 0.85)

    def test_parse_json_embedded_in_text(self) -> None:
        raw_output = """
        Here is the extracted object:
        ```json
        {"bank_name":"CBE","amount":990.0,"transaction_id":"A12","timestamp":"2026-04-01T08:00:00"}
        ```
        """
        result = parse_extraction_output(raw_output)
        self.assertEqual(result["bank_name"], "CBE")
        self.assertAlmostEqual(float(result["amount"]), 990.0)
        self.assertEqual(result["timestamp"], "2026-04-01T08:00:00")
        self.assertEqual(result["confidence"], 0.85)

    def test_parse_missing_fields_confidence(self) -> None:
        raw_output = '{"bank_name":"Awash","amount":null,"transaction_id":"X-9","timestamp":null}'
        result = parse_extraction_output(raw_output)
        self.assertEqual(result["bank_name"], "Awash")
        self.assertIsNone(result["amount"])
        self.assertIsNone(result["timestamp"])
        self.assertEqual(result["confidence"], 0.6)

    def test_fallback_payload(self) -> None:
        fallback = build_fallback_payload()
        self.assertIsNone(fallback["bank_name"])
        self.assertIsNone(fallback["amount"])
        self.assertIsNone(fallback["transaction_id"])
        self.assertIsNone(fallback["timestamp"])
        self.assertEqual(fallback["confidence"], 0.5)


if __name__ == "__main__":
    unittest.main()
