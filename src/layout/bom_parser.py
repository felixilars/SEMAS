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

# Regular expression matching electrical values and ratings
VALUE_PATTERN = re.compile(
    r"(\b\d+/\d+\s*W\b|\b\d+(?:\.\d+)?\s*(?:kohm|mohm|ohm|k\s*ohm|k|M\s*ohm|M|uF|pF|nF|mfd|mf|F|VDC|VAC|V|W|mW|Hz|kHz|MHz|[\u03a9\u2126])\b)",
    re.IGNORECASE,
)

# Regular expression matching tolerance percentages
TOLERANCE_PATTERN = re.compile(r"([\u00b1\+\-/]*\s*\d+(?:\.\d+)?\s*%)")

# Regular expression matching manufacturer part numbers and commercial codes
PART_NUMBER_PATTERN = re.compile(
    r"\b(2S[A-Z]\d{2,4}[A-Z]?|1S\d{3,4}[A-Z]?|1N\d{3,4}[A-Z]?|STK\d{3,5}[I|V|X]*|[A-Z]{2,4}\d{3,5}[A-Z]?|\d{1,3}-\d{3,4}-\d{2,4}-\d{2})\b",
    re.IGNORECASE,
)

# RefDes prefixes to avoid treating circuit identifiers as manufacturer part numbers
COMMON_REFDES_PREFIXES = ("IC", "TR", "VR", "SW", "JK", "CN", "FL", "RY", "SP", "PL")

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

def is_refdes_like(token):
    """ Check whether a token resembles a circuit reference designator rather than a commercial part number.

    Args:
      - token (str) : Candidate token string.
    Returns: True if token matches common RefDes syntax, False otherwise.
    """
    cleaned = str(token).strip().upper()
    for prefix in COMMON_REFDES_PREFIXES:
        if cleaned.startswith(prefix):
            remainder = cleaned[len(prefix):]
            if re.match(r"^\d{1,4}[A-Z]?$", remainder):
                return True
    return False

def extract_specification_fields(text, ref_des=None):
    """ Extract electrical value, tolerance rating, and manufacturer part number from description text.

    Args:
      - text (str) : Raw text string from BOM description or adjacent columns.
      - ref_des (str or None) : Optional reference designator to exclude from part number candidates.
    Returns: Tuple of three strings or None (value, tolerance, part_number).
    """
    if not text:
        return None, None, None

    cleaned = str(text).strip()
    target_text = cleaned
    if ref_des:
        target_text = re.sub(r"\b" + re.escape(str(ref_des)) + r"\b", " ", target_text, flags=re.IGNORECASE).strip()

    # Extract tolerance rating
    tol_match = TOLERANCE_PATTERN.search(target_text)
    tolerance = tol_match.group(1).strip() if tol_match else None

    # Extract electrical value (capacitance, resistance, voltage, power)
    val_match = VALUE_PATTERN.search(target_text)
    value = val_match.group(1).strip() if val_match else None

    # Extract manufacturer part number or catalog code
    part_number = None
    for match in PART_NUMBER_PATTERN.finditer(target_text):
        candidate = match.group(1).strip()
        if not is_refdes_like(candidate):
            part_number = candidate
            break

    return value, tolerance, part_number

class BOMTableParser:
    """ Encapsulates the complete tabular BOM extraction pipeline across detected page columns."""

    # Standard component circuit sub-indices and audio channel suffixes
    VALID_CIRCUIT_SUFFIXES = ("A", "B", "C", "D", "L", "R")

    def __init__(self, min_col_width=150, min_gutter_width=40, max_x_gap=40, max_y_drift=12):
        """ Initialize parser parameters.

        Args:
          - min_col_width (int) : Minimum pixel width for a candidate column.
          - min_gutter_width (int) : Minimum whitespace gutter width.
          - max_x_gap (int) : Maximum horizontal pixel gap for token coalescing.
          - max_y_drift (int) : Maximum vertical pixel drift for token coalescing.
        """
        self.min_col_width = int(min_col_width)
        self.min_gutter_width = int(min_gutter_width)
        self.max_x_gap = int(max_x_gap)
        self.max_y_drift = int(max_y_drift)
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

    def extract_specifications(self, text, ref_des=None):
        """ Extract electrical ratings, tolerance, and part number from candidate text.

        Args:
          - text (str) : Raw text string.
          - ref_des (str or None) : Reference designator to avoid self-matching.
        Returns: Tuple of three strings or None (value, tolerance, part_number).
        """
        return extract_specification_fields(text, ref_des)

    def parse_column(self, col_crop, col_x1, page_dimensions, page_number, ocr_engine):
        """ Process a single cropped column image, coalescing split tokens and extracting items.

        Args:
          - col_crop (np.ndarray) : Pixel array of the column slice.
          - col_x1 (int) : Left boundary pixel coordinate of the column relative to the full page.
          - page_dimensions (tuple) : Full page height and width integers (img_h, img_w).
          - page_number (int) : 1-based page index.
          - ocr_engine (object) : OCR engine instance providing recognize() method.
        Returns: List of BOMItem instances extracted from this column.
        """
        img_h, img_w = page_dimensions
        raw_detections = ocr_engine.recognize(col_crop)

        # Merge horizontally split tokens caused by wide kerning gaps
        clean_detections = coalesce_adjacent_tokens(
            raw_detections,
            max_x_gap=self.max_x_gap,
            max_y_drift=self.max_y_drift,
        )

        column_items = []
        for item in clean_detections:
            raw_text = str(item.get("text", "")).strip()

            # Expand compressed or grouped designators (e.g. 'R101-105', 'C101, 102')
            expanded_refs = expand_refdes_token(raw_text)
            valid_refs = [r for r in expanded_refs if self.is_valid_refdes_token(r)]
            if not valid_refs and " " in raw_text:
                parts = raw_text.split()
                for split_idx in range(len(parts), 0, -1):
                    candidate_prefix = " ".join(parts[:split_idx])
                    candidate_refs = expand_refdes_token(candidate_prefix)
                    if any(self.is_valid_refdes_token(r) for r in candidate_refs):
                        expanded_refs = candidate_refs
                        break

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

                val, tol, part_no = self.extract_specifications(raw_text, ref)

                bom_item = BOMItem(
                    ref_des=ref.upper(),
                    raw_description=raw_text,
                    page_number=page_number,
                    bbox=bbox,
                    value=val,
                    tolerance=tol,
                    part_number=part_no,
                )
                column_items.append(bom_item)

        return column_items

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
            print(
                "[INFO] Processing column "
                + str(col_idx + 1)
                + "/"
                + str(len(columns))
                + ": x in ["
                + str(col_x1)
                + ":"
                + str(col_x2)
                + "]"
            )

            col_items = self.parse_column(col_crop, col_x1, (img_h, img_w), page_number, ocr_engine)
            extracted_items.extend(col_items)

        print("[INFO] Total items extracted across all columns: " + str(len(extracted_items)))
        return extracted_items

    def parse_pages(self, pages_dict, ocr_engine):
        """ Parse multiple manual pages and collect all BOM items into a single list.

        Args:
          - pages_dict (dict) : Mapping of page numbers (int) to image arrays (np.ndarray).
          - ocr_engine (object) : OCR engine instance.
        Returns: Consolidated list of all extracted BOMItem instances.
        """
        all_items = []
        for page_num in sorted(pages_dict.keys()):
            page_img = pages_dict[page_num]
            items = self.parse_page(page_img, page_num, ocr_engine)
            all_items.extend(items)
        return all_items

    def parse_page_dynamic(self, image, page_number, ocr_engine):
        """ Backward compatible alias for parse_page."""
        return self.parse_page(image, page_number, ocr_engine)

BOMParser = BOMTableParser
