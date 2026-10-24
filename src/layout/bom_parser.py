"""
BOM Table Parser Module
=====================================================
Replaces naive hardcoded margins with Dynamic Gutters detection, supporting multi-column pages, shifted tables, and mixed diagram-table layouts.
"""

import re
import numpy as np
import sys

from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.graph.entities import BBox, BOMItem
from src.layout.gutter_detector import find_column_slices

class DynamicBOMParser:
    """ BOM parser that dynamically isolates columns before performing OCR."""

    def __init__(self, min_col_width=150, min_gutter_width=40):
        """ Initialize dynamic parser configuration.

        Args:
          - min_col_width (int) : Minimum pixel width for a candidate column.
          - min_gutter_width (int) : Minimum whitespace gutter width.
        """
        self.min_col_width = int(min_col_width)
        self.min_gutter_width = int(min_gutter_width)
        self.refdes_pattern = re.compile(r"^([A-Z]{1,3}\d{1,4}[A-Z]?)$", re.IGNORECASE)

    def is_valid_refdes_token(self, token_text):
        """ Validate electronic reference designator token syntax.
        
        Args:
          - token_text (str) : Candidate text string.
        Returns: True if valid RefDes token, False otherwise.
        """
        cleaned = re.sub(r"[\s\.,;:]", "", str(token_text)).upper()
        return bool(self.refdes_pattern.match(cleaned))
    
    def parse_page_dynamic(self, image, page_number, ocr_engine):
        """ Detect all column slices dynamically and extract RefDes entities across all columns.
        
        Args:
          - image (np.ndarray) : Source page image array.
          - page_number (int) : 1-based page index.
          - ocr_engine (object) : OCR engine instance providing recognize() method.
        Returns: List of BOMItem instances across all detected columns.
        """
        img_h, img_w = image.shape[:2]
        columns = find_column_slices(image, self.min_col_width, self.min_gutter_width)
        print("[INFO] Dynamically identified " + str(len(columns)) + " column segment(s) on page " + str(page_number))
        extracted_items = []
        for col_idx, (col_x1, col_x2) in enumerate(columns):
            col_crop = image[:, col_x1:col_x2]
            print("[INFO] Processing column " + str(col_idx + 1) + "/" + str(len(columns)) + ": x in [" + str(col_x1) + ":" + str(col_x2) + "]")
            raw_detections = ocr_engine.recognize(col_crop)
            for item in raw_detections:
                text = str(item.get("text", "")).strip()
                if not self.is_valid_refdes_token(text):
                    continue
                crop_box = item.get("bbox")
                if crop_box and len(crop_box) == 4:
                    # Remap from local column crop to full-page normalized coordinates [0.0, 1.0]
                    full_x1 = (col_x1 + crop_box[0]) / float(img_w)
                    full_y1 = crop_box[1] / float(img_h)
                    full_x2 = (col_x1 + crop_box[2]) / float(img_w)
                    full_y2 = crop_box[3] / float(img_h)
                    bbox = BBox(full_x1, full_y1, full_x2, full_y2)
                else:
                    bbox = None
                bom_item = BOMItem(
                    ref_des=text.upper(),
                    raw_description="",
                    page_number=page_number,
                    bbox=bbox,
                )
                extracted_items.append(bom_item)
        print("[INFO] Total items extracted across all columns: " + str(len(extracted_items)))
        return extracted_items