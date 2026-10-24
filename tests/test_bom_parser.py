"""
Unit Tests for BOM Parser
==================================================
Validates margin slicing math, candidate regex filtering, and coordinate remapping.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.append(str(Path(__file__).parent.parent))

from src.layout.bom_parser import NaiveBOMParser

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

def test_crop_refdes_column_dimensions():
    """ Verify horizontal percentage slice calculation."""
    parser = NaiveBOMParser(left_ratio=0.10, right_ratio=0.25)
    dummy_img = np.zeros((1000, 2000, 3), dtype=np.uint8)

    crop, x1, x2 = parser.crop_refdes_column(dummy_img)

    assert x1 == 200  # 10% of 2000
    assert x2 == 500  # 25% of 2000
    assert crop.shape == (1000, 300, 3)

def test_is_valid_refdes_token_positives():
    """ Verify accepted electronics reference designators."""
    parser = NaiveBOMParser()
    assert parser.is_valid_refdes_token("R101") is True
    assert parser.is_valid_refdes_token("C205") is True
    assert parser.is_valid_refdes_token("Q701") is True
    assert parser.is_valid_refdes_token("IC01") is True
    assert parser.is_valid_refdes_token("R101A") is True

def test_is_valid_refdes_token_negatives():
    """ Verify rejection of non-refdes strings, headers, and descriptions."""
    parser = NaiveBOMParser()
    assert parser.is_valid_refdes_token("RESISTOR") is False
    assert parser.is_valid_refdes_token("47k") is False
    assert parser.is_valid_refdes_token("5%") is False
    assert parser.is_valid_refdes_token("ELECTROLYTIC") is False
    assert parser.is_valid_refdes_token("PARTS LIST") is False

def test_parse_page_naive_coordinate_remapping():
    """ Verify that bounding boxes in cropped space map back to whole-page normalized space."""
    parser = NaiveBOMParser(left_ratio=0.10, right_ratio=0.25)
    dummy_img = np.zeros((1000, 2000, 3), dtype=np.uint8)

    # In crop of width 300 px (x_offset = 200 px), item is located at [10, 50, 60, 80]
    mock_detections = [
        {"text": "R102", "bbox": [10, 50, 60, 80], "confidence": 0.95},
        {"text": "DESCRIPTION", "bbox": [80, 50, 200, 80], "confidence": 0.90},  # should be filtered out
    ]
    mock_engine = MockOCREngine(mock_detections)

    items = parser.parse_page_naive(dummy_img, 6, mock_engine)

    assert len(items) == 1
    item = items[0]
    assert item.ref_des == "R102"
    assert item.page_number == 6
    assert item.bbox is not None

    # Full page X coordinates:
    # x1 = (200 + 10) / 2000 = 0.105
    # x2 = (200 + 60) / 2000 = 0.130
    # y1 = 50 / 1000 = 0.050
    # y2 = 80 / 1000 = 0.080
    assert round(item.bbox.x1, 3) == 0.105
    assert round(item.bbox.x2, 3) == 0.130
    assert round(item.bbox.y1, 3) == 0.050
    assert round(item.bbox.y2, 3) == 0.080
