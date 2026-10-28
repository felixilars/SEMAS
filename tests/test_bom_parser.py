"""
Unit Tests for BOM Parser
=========================
Validates candidate regex filtering, whole-page coordinate remapping, phantom designator rejection, specification extraction, and full pipeline execution with BOMTableParser.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.append(str(Path(__file__).parent.parent))

from src.layout.bom_parser import (
    BOMTableParser,
    BOMParser,
    is_spec_unit,
    extract_specification_fields,
)
from src.layout.refdes_expander import expand_refdes_token
from src.layout import BOMTableParser as ExportedBOMTableParser

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

def test_bom_table_parser_alias():
    """ Verify that BOMParser is an alias to BOMTableParser for backward compatibility."""
    assert BOMParser is BOMTableParser
    assert ExportedBOMTableParser is BOMTableParser

def test_is_valid_refdes_token_positives():
    """ Verify accepted electronics reference designators."""
    parser = BOMTableParser()
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
    parser = BOMTableParser()
    assert parser.is_valid_refdes_token("RESISTOR") is False
    assert parser.is_valid_refdes_token("47k") is False
    assert parser.is_valid_refdes_token("5%") is False
    assert parser.is_valid_refdes_token("ELECTROLYTIC") is False
    assert parser.is_valid_refdes_token("PARTS LIST") is False

def test_is_spec_unit_detection():
    """ Verify detection of voltage, capacitance, resistance, and power rating strings."""
    assert is_spec_unit("500V") is True
    assert is_spec_unit("250V") is True
    assert is_spec_unit("50V") is True
    assert is_spec_unit("12VDC") is True
    assert is_spec_unit("47k") is True
    assert is_spec_unit("100kohm") is True
    assert is_spec_unit("100uF") is True
    assert is_spec_unit("0.01uF") is True
    assert is_spec_unit("220pF") is True
    assert is_spec_unit("1/4W") is True
    assert is_spec_unit("1/2W") is True
    assert is_spec_unit("5%") is True

    assert is_spec_unit("R101") is False
    assert is_spec_unit("C205") is False
    assert is_spec_unit("Q701") is False

def test_reject_phantom_refdes_tokens():
    """ Verify rejection of phantom designators contaminated with rating units."""
    parser = BOMTableParser()
    assert parser.is_valid_refdes_token("R500V") is False
    assert parser.is_valid_refdes_token("R250V") is False
    assert parser.is_valid_refdes_token("C50V") is False
    assert parser.is_valid_refdes_token("R10K") is False
    assert parser.is_valid_refdes_token("R47K") is False
    assert parser.is_valid_refdes_token("C100UF") is False
    assert parser.is_valid_refdes_token("R1/4W") is False

def test_expand_comma_list_ignores_electrical_ratings():
    """ Verify comma-delimited expansion does not inherit prefix onto rating values."""
    result_cap = expand_refdes_token("C101, 102, 50V")
    assert result_cap == ["C101", "C102"]

    result_res = expand_refdes_token("R101, 102, 1/4W")
    assert result_res == ["R101", "R102"]

def test_bom_parser_coordinate_remapping():
    """ Verify that bounding boxes in column space map back to whole-page normalized space."""
    parser = BOMTableParser(min_col_width=100, min_gutter_width=30)
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

    assert round(item.bbox.x1, 3) == 0.105
    assert round(item.bbox.x2, 3) == 0.130
    assert round(item.bbox.y1, 3) == 0.050
    assert round(item.bbox.y2, 3) == 0.080

def test_bom_parser_coalesce_and_expand_pipeline():
    """ Verify BOMTableParser integrates dynamic gutters, token coalescing, and range expansion."""
    parser = BOMTableParser(min_col_width=100, min_gutter_width=30)

    dummy_img = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    dummy_img[100:900, 100:400] = 0
    dummy_img[100:900, 600:900] = 0

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

def test_extract_specification_fields_resistor():
    """ Verify value and tolerance extraction from resistor description strings."""
    val, tol, part = extract_specification_fields("Carbon Resistor 47k Ohm 5% 1/4W")
    assert val is not None
    assert "47k" in val
    assert tol == "5%"
    assert part is None

def test_extract_specification_fields_capacitor():
    """ Verify capacitance and tolerance extraction from capacitor descriptions."""
    val, tol, part = extract_specification_fields("Electrolytic 100uF 50V +/-20%")
    assert val == "100uF"
    assert tol == "+/-20%"
    assert part is None

def test_extract_specification_fields_semiconductor():
    """ Verify transistor and IC part number extraction."""
    val, tol, part = extract_specification_fields("Silicon Transistor 2SC1815-GR NPN")
    assert part == "2SC1815"

    val_ic, tol_ic, part_ic = extract_specification_fields("Dual Op-Amp TA7136P SIP-7")
    assert part_ic == "TA7136P"

def test_extract_specification_fields_catalog_number():
    """ Verify catalog part number extraction in Sony standard format."""
    val, tol, part = extract_specification_fields("Part 1-247-065-00 Carbon Film 2.2k 5%")
    assert part == "1-247-065-00"
    assert tol == "5%"
    assert val == "2.2k"

def test_extract_specification_fields_refdes_exclusion():
    """ Verify that RefDes identifiers are not falsely matched as manufacturer part numbers."""
    val, tol, part = extract_specification_fields("IC101 TA7136P PRE-AMPLIFIER", ref_des="IC101")
    assert part == "TA7136P"

def test_extract_specification_fields_empty():
    """ Verify graceful handling of empty or whitespace text."""
    val, tol, part = extract_specification_fields("")
    assert val is None
    assert tol is None
    assert part is None

    val_none, tol_none, part_none = extract_specification_fields(None)
    assert val_none is None
    assert tol_none is None
    assert part_none is None

def test_bom_parser_populates_specification_fields():
    """ Verify that BOMTableParser populates value, tolerance, and part_number on parsed BOMItem instances."""
    parser = BOMTableParser(min_col_width=100, min_gutter_width=30)
    dummy_img = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    dummy_img[100:900, 100:800] = 0

    mock_detections = [
        {"text": "R101 47k 5% 1-247-065-00", "bbox": [20, 100, 300, 130], "confidence": 0.98},
    ]
    mock_engine = MockOCREngine(mock_detections)

    items = parser.parse_page(dummy_img, 1, mock_engine)
    assert len(items) == 1
    item = items[0]
    assert item.ref_des == "R101"
    assert item.value == "47k"
    assert item.tolerance == "5%"
    assert item.part_number == "1-247-065-00"

def test_bom_table_parser_parse_pages():
    """ Verify multi-page dictionary parsing across consecutive pages."""
    parser = BOMTableParser(min_col_width=100, min_gutter_width=30)

    dummy_img1 = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    dummy_img1[100:900, 100:800] = 0
    dummy_img2 = np.full((1000, 1000, 3), 255, dtype=np.uint8)
    dummy_img2[100:900, 100:800] = 0

    mock_engine = MockOCREngine([
        {"text": "R101 47k 5%", "bbox": [20, 100, 200, 130], "confidence": 0.98},
    ])

    pages = {1: dummy_img1, 2: dummy_img2}
    items = parser.parse_pages(pages, mock_engine)

    assert len(items) == 2
    assert items[0].page_number == 1
    assert items[1].page_number == 2