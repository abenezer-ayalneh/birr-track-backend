"""Tests for PaddleOCR raw output normalization (no Paddle runtime required)."""

from __future__ import annotations

import unittest

from app.services.ocr_result_normalize import normalize_paddle_ocr_raw


class TestNormalizePaddleOCRRaw(unittest.TestCase):
    """Exercise normalize_paddle_ocr_raw for 2.x and 3.x shapes."""

    def test_paddlex_predict_dict_shape(self) -> None:
        raw = [
            {
                "res": {
                    "rec_texts": ["Thank You!", "Success"],
                    "rec_scores": [0.99, 0.97],
                }
            }
        ]
        lines = normalize_paddle_ocr_raw(raw)
        self.assertEqual([t for t, _ in lines], ["Thank You!", "Success"])
        self.assertAlmostEqual(lines[0][1], 0.99)
        self.assertAlmostEqual(lines[1][1], 0.97)

    def test_paddlex_top_level_rec_texts(self) -> None:
        raw = [{"rec_texts": ["only"], "rec_scores": [0.5]}]
        lines = normalize_paddle_ocr_raw(raw)
        self.assertEqual(lines, [("only", 0.5)])

    def test_legacy_nested_list_shape(self) -> None:
        bbox = [[0, 0], [10, 0], [10, 10], [0, 10]]
        raw = [[(bbox, ("LegacyLine", 0.88))]]
        lines = normalize_paddle_ocr_raw(raw)
        self.assertEqual(lines, [("LegacyLine", 0.88)])

    def test_empty_paddlex(self) -> None:
        raw = [{"res": {"rec_texts": [], "rec_scores": []}}]
        self.assertEqual(normalize_paddle_ocr_raw(raw), [])
