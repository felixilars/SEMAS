"""
Unit Tests for Entities
=====================================
Validates BBox geometry boundary enforcement, pixel transformations, and BOMItem initialization.
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.graph.entities import BBox, BOMItem

def test_bbox_initialization_valid():
    """ Verify correct assignment of valid normalized coordinates."""
    box = BBox(0.1, 0.2, 0.5, 0.8)
    assert box.x1 == 0.1
    assert box.y1 == 0.2
    assert box.x2 == 0.5
    assert box.y2 == 0.8

def test_bbox_invalid_ordering_raises_error():
    """ Verify exception when x2 < x1 or y2 < y1."""
    with pytest.raises(ValueError) as excinfo:
        BBox(0.6, 0.2, 0.3, 0.8)
    assert "x2" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        BBox(0.1, 0.9, 0.5, 0.3)
    assert "y2" in str(excinfo.value)

def test_bbox_pixel_conversion():
    """ Verify mapping from normalized [0, 1] space to absolute pixel space."""
    box = BBox(0.1, 0.2, 0.5, 0.8)
    pixels = box.to_pixel(1000, 2000)
    assert pixels == [100, 400, 500, 1600]

def test_bbox_area_calculation():
    """ Verify normalized area calculation."""
    box = BBox(0.1, 0.2, 0.5, 0.6)
    expected_area = (0.5 - 0.1) * (0.6 - 0.2)
    assert round(box.compute_area(), 4) == round(expected_area, 4)

def test_bom_item_serialization():
    """ Verify BOMItem initialization, normalization, and dictionary export."""
    box = BBox(0.05, 0.10, 0.25, 0.15)
    item = BOMItem(" r102 ", "Carbon Resistor 47k Ohm 5%", 6, box)

    assert item.ref_des == "R102"
    assert item.page_number == 6
    assert item.raw_description == "Carbon Resistor 47k Ohm 5%"

    data = item.to_dict()
    assert data["ref_des"] == "R102"
    assert data["page_number"] == 6
    assert data["bbox"]["x1"] == 0.05
    assert data["value"] is None
    assert data["tolerance"] is None
    assert data["part_number"] is None

def test_bom_item_extended_fields_serialization():
    """ Verify BOMItem initialization and dictionary export with value, tolerance, and part number."""
    box = BBox(0.05, 0.10, 0.25, 0.15)
    item = BOMItem(
        ref_des="R101",
        raw_description="Carbon Resistor 47k Ohm 5% 1/4W",
        page_number=6,
        bbox=box,
        value="47k",
        tolerance="5%",
        part_number="1-247-065-00",
    )

    assert item.ref_des == "R101"
    assert item.value == "47k"
    assert item.tolerance == "5%"
    assert item.part_number == "1-247-065-00"

    data = item.to_dict()
    assert data["value"] == "47k"
    assert data["tolerance"] == "5%"
    assert data["part_number"] == "1-247-065-00"