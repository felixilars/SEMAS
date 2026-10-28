"""
Unit Tests for Schematic OCR Extractor
======================================
Validates coordinate boundary clamping, text and specification splitting, multi-angle label extraction, and batch component processing.
"""

import json
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.append(str(Path(__file__).parent.parent))

from ocr_engine.base import BaseOCREngine
from ocr_engine.schematic_extractor import SchematicOCRExtractor
from ocr_engine import SchematicOCRExtractor as ExportedExtractor

class MockSchematicOCREngine(BaseOCREngine):
    """ Mock OCR engine returning canned recognition results for test images."""

    def __init__(self, canned_text="R101 10k", canned_conf=0.95):
        """ Initialize mock engine with fixed return values.

        Args:
          - canned_text (str) : Recognition string.
          - canned_conf (float) : Confidence score.
        """
        self.canned_text = canned_text
        self.canned_conf = canned_conf

    def read_text(self, crop_img):
        """ Return canned text and confidence.

        Args:
          - crop_img (np.ndarray) : Image array.
        Returns: Tuple of (canned_text, canned_conf).
        """
        if crop_img is None or crop_img.size == 0:
            return "", 0.0
        return self.canned_text, self.canned_conf

    def extract_text_boxes(self, image_np):
        """ Mock bounding boxes extraction.

        Args:
          - image_np (np.ndarray) : Ignored image.
        Returns: Empty list.
        """
        return []

def test_schematic_extractor_export():
    """ Verify package export from ocr_engine."""
    assert ExportedExtractor is SchematicOCRExtractor


def test_crop_box_boundary_clamping():
    """ Verify safe coordinate clamping and padding around image boundaries."""
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    extractor = SchematicOCRExtractor(ocr_engine=MockSchematicOCREngine(), padding=5)

    # Box exceeding top-left boundary
    crop_tl = extractor.crop_box(dummy_img, [0, 0, 20, 20])
    assert crop_tl is not None
    assert crop_tl.shape == (25, 25, 3)

    # Box exceeding bottom-right boundary
    crop_br = extractor.crop_box(dummy_img, [80, 80, 100, 100])
    assert crop_br is not None
    assert crop_br.shape == (25, 25, 3)

def test_crop_box_invalid_coordinates():
    """ Verify None return when x2 < x1 or y2 < y1."""
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    extractor = SchematicOCRExtractor(ocr_engine=MockSchematicOCREngine())

    assert extractor.crop_box(dummy_img, [50, 50, 20, 40]) is None
    assert extractor.crop_box(dummy_img, [20, 50, 40, 20]) is None

def test_extract_label_with_spec_separation():
    """ Verify RefDes extraction and separation of attached electrical ratings."""
    dummy_img = np.zeros((200, 200, 3), dtype=np.uint8)
    mock_engine = MockSchematicOCREngine(canned_text="R184 33k", canned_conf=0.98)
    extractor = SchematicOCRExtractor(ocr_engine=mock_engine)

    result = extractor.extract_label(dummy_img, [50, 50, 150, 80])

    assert result["raw_text"] == "R184 33k"
    assert result["ref_des"] == "R184"
    assert result["spec_value"] == "33k"
    assert result["confidence"] == 0.98
    assert result["rotation_deg"] == 0

def test_extract_schematic_components_batch():
    """ Verify batch processing of multiple component bounding boxes."""
    dummy_img = np.zeros((300, 300, 3), dtype=np.uint8)
    mock_engine = MockSchematicOCREngine(canned_text="C205 100uF", canned_conf=0.92)
    extractor = SchematicOCRExtractor(ocr_engine=mock_engine)

    boxes = [
        [10, 10, 50, 30],
        [60, 60, 100, 80],
    ]
    results = extractor.extract_schematic_components(dummy_img, boxes)

    assert len(results) == 2
    assert results[0]["box_index"] == 0
    assert results[0]["ref_des"] == "C205"
    assert results[0]["spec_value"] == "100uF"
    assert results[1]["box_index"] == 1

def test_export_detections(tmp_path):
    """ Verify JSON export serialization of schematic detection records."""
    extractor = SchematicOCRExtractor(ocr_engine=MockSchematicOCREngine())
    detections = [
        {
            "box_index": 0,
            "raw_text": "Q101",
            "ref_des": "Q101",
            "spec_value": None,
            "confidence": 0.99,
            "rotation_deg": 0,
            "bbox": [10, 10, 40, 30],
        }
    ]

    target_file = tmp_path / "schematic_detections.json"
    extractor.export_detections(detections, target_file)

    assert target_file.exists()
    with open(target_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert len(loaded) == 1
    assert loaded[0]["ref_des"] == "Q101"