"""
Unit Tests for Token Coalescing
=======================================
Validates horizontal merging of prefix-numeric pairs and bounds expansion.
"""

import sys
from pathlib import Path
import pytest

# Ensure repository root is on sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.layout.token_coalescer import (
    is_prefix_token,
    is_numeric_index_token,
    coalesce_adjacent_tokens,
)


def test_prefix_and_numeric_validation():
    """ Verify detection of isolated prefixes and numeric indices."""
    assert is_prefix_token("R") is True
    assert is_prefix_token("C") is True
    assert is_prefix_token("Q") is True
    assert is_prefix_token("IC") is True
    assert is_prefix_token("RESISTOR") is False

    assert is_numeric_index_token("101") is True
    assert is_numeric_index_token("205A") is True
    assert is_numeric_index_token("47k") is False


def test_coalesce_adjacent_tokens_success():
    """ Verify severed 'R' and '113' tokens merge into single 'R113' token."""
    raw_boxes = [
        {"text": "R", "bbox": [10, 100, 25, 120], "confidence": 0.95},
        {"text": "113", "bbox": [30, 100, 65, 120], "confidence": 0.97},
        {"text": "Carbon 10k", "bbox": [120, 100, 250, 120], "confidence": 0.91},
    ]

    coalesced = coalesce_adjacent_tokens(raw_boxes, max_x_gap=40, max_y_drift=10)

    assert len(coalesced) == 2
    merged = coalesced[0]
    assert merged["text"] == "R113"
    assert merged["bbox"] == [10, 100, 65, 120]
    assert round(merged["confidence"], 2) == 0.96


def test_coalesce_does_not_merge_when_gap_too_large():
    """ Verify tokens do not merge if horizontal gap exceeds max_x_gap."""
    raw_boxes = [
        {"text": "R", "bbox": [10, 100, 25, 120], "confidence": 0.95},
        {"text": "113", "bbox": [95, 100, 130, 120], "confidence": 0.97},
    ]

    coalesced = coalesce_adjacent_tokens(raw_boxes, max_x_gap=40, max_y_drift=10)

    assert len(coalesced) == 2
    assert coalesced[0]["text"] == "R"
    assert coalesced[1]["text"] == "113"


def test_coalesce_internal_space_normalization():
    """ Verify 'R 102' within a single box is collapsed to 'R102'."""
    raw_boxes = [
        {"text": "R 102", "bbox": [10, 100, 65, 120], "confidence": 0.94},
    ]

    coalesced = coalesce_adjacent_tokens(raw_boxes)

    assert len(coalesced) == 1
    assert coalesced[0]["text"] == "R102"
