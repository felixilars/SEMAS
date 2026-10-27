"""
BOM Table Parser Module
=======================
Extracts electronic component references from tabular Bill of Materials pages using dynamic column segmentation, horizontal token coalescing, and reference range expansion.
"""

from pathlib import Path
import re
import sys
import numpy as np

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.graph.entities import BBox, BOMItem
from src.layout.gutter_detector import find_column_slices
from src.layout.token_coalescer import coalesce_adjacent_tokens
from src.layout.refdes_expander import expand_refdes_token

# Regular expression identifying standard electrical rating units and values
SPEC_UNIT_PATTERN = re.compile(
    r"^\d+(?:\.\d+)?\s*(?:VDC|VAC|V|UF|PF|NF|MFD|MF|F|KOHM|MOHM|OHM|K|M|W|MW|HZ|KHZ|MHZ|%|DB)$",
    re.IGNORECASE,
)

# Fraction wattage ratings, e.g. '1/4W', '1/2W', '1/8W'
FRACTION_WATT_PATTERN = re.compile(r"^\d+/\d+\s*W$", re.IGNORECASE)

# Prohibited suffix characters that represent electrical units rather than circuit channel or revision letters
UNIT_SUFFIX_CHARS = ("V", "K", "M", "W", "F", "H")

def is_spec_unit(token):
    """ Check whether a candidate token represents an electrical technical specification.

    Args:
      - token (str) : Candidate text string from OCR.
    Returns: True if token matches an electrical specification or rating, False otherwise.
    """
    if not token:
        return False
    cleaned = str(token).strip()
    if bool(SPEC_UNIT_PATTERN.match(cleaned)):
        return True
    if bool(FRACTION_WATT_PATTERN.match(cleaned)):
        return True
    return False

class BOMParser:
    """ BOM parser that dynamically isolates columns, coalesces split tokens, and expands ranges."""

    # Standard component circuit sub-indices and audio channel suffixes
    # (e.g. 'A', 'B', 'C', 'D' for multi-gate ICs; 'L', 'R' for stereo left/right channels)
    VALID_CIRCUIT_SUFFIXES = ("A", "B", "C", "D", "L", "R")

    def __init__(self, min_col_width=150, min_gutter_width=40):
        """ Initialize parser configuration.

        Args:
          - min_col_width (int) : Minimum pixel width for a candidate column.
          - min_gutter_width (int) : Minimum whitespace gutter width.
        Returns: None.
        """
        self.min_col_width = int(min_col_width)
        self.min_gutter_width = int(min_gutter_width)
        self.refdes_pattern = re.compile(r"^([A-Z]{1,3}\d{1,4})([A-Z])?$", re.IGNORECASE)

    def is_valid_refdes_token(self, token_text):
        """ Validate electronic reference designator token syntax and reject rating units.

        Args:
          - token_text (str) : Candidate text string.
        Returns: True if valid RefDes token, False otherwise.
        """
        if not token_text:
            return False

        cleaned = re.sub(r"[\s\.,;:]", "", str(token_text)).upper()

        # 1. Reject pure electrical specification units (e.g. '500V', '47K', '100UF', '1/4W')
        if is_spec_unit(cleaned):
            return False

        # 2. Reject phantom designators terminating in electrical units (e.g. 'R500V', 'C50V', 'R10K')
        if any(cleaned.endswith(unit) for unit in UNIT_SUFFIX_CHARS):
            return False

        # 3. Match base reference designator pattern
        match = self.refdes_pattern.match(cleaned)
        if not match:
            return False

        # 4. If an optional sub-unit letter suffix is present, validate against allowed suffixes
        suffix = match.group(2)
        if suffix and suffix.upper() not in self.VALID_CIRCUIT_SUFFIXES:
            return False

        return True

    def parse_page(self, image, page_number, ocr_engine):
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

            # Merge horizontally split tokens caused by wide kerning gaps
            clean_detections = coalesce_adjacent_tokens(raw_detections, max_x_gap=40, max_y_drift=12)

            for item in clean_detections:
                raw_text = str(item.get("text", "")).strip()

                # Expand compressed or grouped designators (e.g. 'R101-105', 'C101, 102')
                expanded_refs = expand_refdes_token(raw_text)
                if not expanded_refs:
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

                for ref in expanded_refs:
                    if not self.is_valid_refdes_token(ref):
                        continue

                    bom_item = BOMItem(
                        ref_des=ref.upper(),
                        raw_description="",
                        page_number=page_number,
                        bbox=bbox,
                    )
                    extracted_items.append(bom_item)

        print("[INFO] Total items extracted across all columns: " + str(len(extracted_items)))
        return extracted_items

    def parse_page_dynamic(self, image, page_number, ocr_engine):
        """ Backward compatible alias for parse_page."""
        return self.parse_page(image, page_number, ocr_engine)