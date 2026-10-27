"""
Unit Tests for Dynamic Gutters Algorithm
================================================
Validates vertical projection histogram calculation and whitespace gutter isolation.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

# Ensure repository root is on sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.layout.gutter_detector import (
    compute_vertical_projection,
    detect_vertical_gutters,
    find_column_slices,
)

def test_vertical_projection_synthetic_stripes():
    """ Verify projection histogram peaks over vertical dark stripes."""
    canvas = np.full((500, 1000), 255, dtype=np.uint8)
    canvas[:, 200:400] = 0

    proj = compute_vertical_projection(canvas)

    assert proj.shape == (1000,)
    assert proj[50] == 0
    assert proj[600] == 0
    assert proj[300] == 500 * 255

def test_detect_vertical_gutters_multi_column():
    """ Verify detection of whitespace gutters separating two text blocks."""
    canvas = np.full((500, 1000), 255, dtype=np.uint8)
    canvas[:, 100:400] = 0
    canvas[:, 600:900] = 0

    gutters = detect_vertical_gutters(canvas, min_gutter_width=40)

    assert len(gutters) >= 2
    middle_gutter_found = any(g[0] <= 450 and g[1] >= 550 for g in gutters)
    assert middle_gutter_found is True

def test_find_column_slices_isolates_both_columns():
    """ Verify find_column_slices returns separate content slices for columns."""
    canvas = np.full((500, 1000), 255, dtype=np.uint8)
    canvas[:, 100:400] = 0
    canvas[:, 600:900] = 0

    columns = find_column_slices(canvas, min_column_width=150, min_gutter_width=40)

    assert len(columns) == 2
    assert columns[0][0] <= 100
    assert columns[0][1] >= 400
    assert columns[1][0] <= 600
    assert columns[1][1] >= 900
