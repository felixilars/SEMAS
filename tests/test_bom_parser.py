"""
Unit Tests for BOM Parser
=========================
Validates candidate regex filtering, whole-page coordinate remapping, phantom designator rejection, and full pipeline execution with dynamic gutters, token coalescing, and range expansion.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.append(str(Path(__file__).parent.parent))

from src.layout.bom_parser import BOMParser, is_spec_unit
from src.layout.refdes_expander import expand_refdes_token


class MockOCREngine:
    """ Mock OCR engine returning pre-defined text boxes for testing."""

    def __init__(self, mock_results):
        """ Initialize mock engine with fixture detections.

        Args:
          - mock_results (list) : List of fixture prediction dictionaries.
        """
        self.mock_results = mock_results

    def recognize(self, image):
        """ Return canned bounding boxes regardless of input pixels.

        Args:
          - image (np.ndarray) : Ignored test image.
        Returns: List of detection dictionaries.
        """
        return self.mock_results


def test_is_valid_refdes_token_positives():
    """ Verify accepted electronics reference designators."""
    parser = BOMParser()
    assert parser.is_valid_refdes_token("R101") is True
    assert parser.is_valid_refdes_token("C205") is True
    assert parser.is_valid_refdes_token("Q701") is True
    assert parser.is_valid_refdes_token("IC01") is True
    assert parser.is_valid_refdes_token("R101A") is True
    assert parser.is_valid_refdes_token("C205B") is True
    assert parser.is_valid_refdes_token("Q101L") is True
    assert parser.is_valid_refdes_token("Q101R") is True


def test_is_valid_refdes_token_negatives():
    """ Verify rejection of non-refdes strings, headers, and descriptions."""
    parser = BOMParser()
    assert parser.is_valid_refdes_token("RESISTOR") is False
    assert parser.is_valid_refdes_token("47k") is False
    assert parser.is_valid_refdes_token("5%") is False
    assert parser.is_valid_refdes_token("ELECTROLYTIC") is False
    assert parser.is_valid_refdes_token("PARTS LIST") is False


def test_is_spec_unit_detection():
    """ Verify detection of voltage, capacitance, resistance, and power rating strings."""
    # Voltage ratings
    assert is_spec_unit("500V") is True
    assert is_spec_unit("250V") is True
    assert is_spec_unit("50V") is True
    assert is_spec_unit("12VDC") is True

    # Resistance and capacitance
    assert is_spec_unit("47k") is True
    assert is_spec_unit("100kohm") is True
    assert is_spec_unit("100uF") is True
    assert is_spec_unit("0.01uF") is True
    assert is_spec_unit("220pF") is True

    # Power and tolerance
    assert is_spec_unit("1/4W") is True
    assert is_spec_unit("1/2W") is True
    assert is_spec_unit("5%") is True

    # Legitimate RefDes must NOT be flagged as spec units
    assert is_spec_unit("R101") is False
    assert is_spec_unit("C205") is False
    assert is_spec_unit("Q701") is False


def test_reject_phantom_refdes_tokens():
    """ Verify rejection of phantom designators contaminated with rating units."""
    parser = BOMParser()

    # Contaminated with voltage unit 'V'
    assert parser.is_valid_refdes_token("R500V") is False
    assert parser.is_valid_refdes_token("R250V") is False
    assert parser.is_valid_refdes_token("C50V") is False

    # Contaminated with resistance/capacitance unit 'K', 'M', 'U'
    assert parser.is_valid_refdes_token("R10K") is False
    assert parser.is_valid_refdes_token("R47K") is False
    assert parser.is_valid_refdes_token("C100UF") is False

    # Contaminated with power unit 'W'
    assert parser.is_valid_refdes_token("R1/4W") is False


def test_expand_comma_list_ignores_electrical_ratings():
    """ Verify comma-delimited expansion does not inherit prefix onto rating values."""
    # '50V' must NOT become 'C50V'
    result_cap = expand_refdes_token("C101, 102, 50V")
    assert result_cap == ["C101", "C102"]

    # '1/4W' must NOT become 'R1/4W'
    result_res = expand_refdes_token("R101, 102, 1/4W")
    assert result_res == ["R101", "R102"]


def test_bom_parser_coordinate_remapping():
    """ Verify that bounding boxes in column space map back to whole-page normalized space."""
    parser = BOMParser(min_col_width=100, min_gutter_width=30)
    # Synthetic image (1000x2000): white page with single text column between x=200 and x=500
    dummy_img = np.full((1000, 2000, 3), 255, dtype=np.uint8)
    dummy_img[50:950, 200:500] = 0

    mock_detections = [
        {"text": "R102", "bbox": [10, 50, 60, 80], "confidence": 0.95},
        {"text": "DESCRIPTION", "bbox": [80, 50, 200, 80], "confidence": 0.90},
    ]
    mock_engine = MockOCREngine(mock_detections)

    items = parser.parse_page(dummy_img, 6, mock_engine)

    assert len(items) == 1
    item = items[0]
    assert item.ref_des == "R102"
    assert item.page_number == 6
    assert item.bbox is not None

    # Full page X coordinates (col starts at x=200):
    # x1 = (200 + 10) / 2000 = 0.105
    # x2 = (200 + 60) / 2000 = 0.130
    # y1 = 50 / 1000 = 0.050
    # y2 = 80 / 1000 = 0.080
    assert round(item.bbox.x1, 3) == 0.105
    assert round(item.bbox.x2, 3) == 0.130
    assert round(item.bbox.y1, 3) == 0.050
    assert round(item.bbox.y2, 3) == 0.080


def test_bom_parser_coalesce_and_expand_pipeline():
    """ Verify BOMParser integrates dynamic gutters, token coalescing, and range expansion."""
    parser = BOMParser(min_col_width=100, min_gutter_width=30)

    # Synthetic image (1000x1000): white page with two text blocks
    # Content col 1: x in [50, 450], Gutter: [450, 550], Content col 2: [550, 950]
    dummy_img = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    dummy_img[100:900, 100:400] = 0
    dummy_img[100:900, 600:900] = 0

    # Column detections:
    # 1. Split token: 'R' + '101' -> should coalesce into 'R101'
    # 2. Range token: 'C201-203' -> should expand into 'C201', 'C202', 'C203'
    # 3. Non-refdes token: 'RESISTOR' -> should be filtered out
    # 4. Rating unit: '500V' -> should be filtered out
    mock_detections = [
        {"text": "R", "bbox": [20, 100, 40, 130], "confidence": 0.99},
        {"text": "101", "bbox": [45, 100, 90, 130], "confidence": 0.98},
        {"text": "C201-203", "bbox": [20, 200, 120, 230], "confidence": 0.95},
        {"text": "RESISTOR", "bbox": [150, 100, 300, 130], "confidence": 0.90},
        {"text": "500V", "bbox": [20, 300, 80, 330], "confidence": 0.92},
    ]
    mock_engine = MockOCREngine(mock_detections)

    items = parser.parse_page(dummy_img, 1, mock_engine)
    ref_names = [it.ref_des for it in items]

    assert "R101" in ref_names
    assert "C201" in ref_names
    assert "C202" in ref_names
    assert "C203" in ref_names
    assert "RESISTOR" not in ref_names
    assert "500V" not in ref_names
