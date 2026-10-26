"""
BOM Table Parser Module
=======================
Extracts electronic component references from tabular Bill of Materials pages using
dynamic column segmentation, horizontal token coalescing, and reference range expansion.
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


class NaiveBOMParser:
    """ Baseline parser relying on fixed horizontal percentage margins."""

    def __init__(self, left_ratio=0.10, right_ratio=0.25):
        """ Initialize parser with empirical margin boundaries.

        Args:
          - left_ratio (float) : Left margin ratio of page width (default: 0.10).
          - right_ratio (float) : Right margin ratio of page width (default: 0.25).
        Returns: None.
        """
        self.left_ratio = float(left_ratio)
        self.right_ratio = float(right_ratio)
        self.refdes_pattern = re.compile(r"^([A-Z]{1,3}\d{1,4}[A-Z]?)$", re.IGNORECASE)

    def crop_refdes_column(self, image):
        """ Crop the horizontal slice presumed to contain reference designator text.

        Args:
          - image (np.ndarray) : Source 300 DPI page image array.
        Returns: Tuple of (cropped_image, x_start_px, x_end_px).
        """
        if image is None or image.size == 0:
            raise ValueError("Input image is empty or invalid")

        height, width = image.shape[:2]
        x_start_px = int(width * self.left_ratio)
        x_end_px = int(width * self.right_ratio)

        cropped_image = image[:, x_start_px:x_end_px]
        return cropped_image, x_start_px, x_end_px

    def is_valid_refdes_token(self, token_text):
        """ Check whether a candidate string matches reference designator syntax.

        Args:
          - token_text (str) : Raw text string from OCR detection.
        Returns: True if token matches alphanumeric pattern, False otherwise.
        """
        cleaned = re.sub(r"[\s\.,;:]", "", str(token_text)).upper()
        return bool(self.refdes_pattern.match(cleaned))

    def parse_page_naive(self, image, page_number, ocr_engine):
        """ Extract BOM items by running OCR strictly on the statically cropped column.

        Args:
          - image (np.ndarray) : Source page image array.
          - page_number (int) : 1-based index of the manual page.
          - ocr_engine (object) : OCR engine instance providing a recognize() method.
        Returns: List of BOMItem objects detected within the cropped region.
        """
        cropped_img, x_offset, _ = self.crop_refdes_column(image)
        img_h, img_w = image.shape[:2]

        print("[INFO] Running baseline OCR on cropped column: width=" + str(cropped_img.shape[1]) + ", height=" + str(cropped_img.shape[0]))

        raw_detections = ocr_engine.recognize(cropped_img)
        extracted_items = []

        for item in raw_detections:
            text = str(item.get("text", "")).strip()
            if not self.is_valid_refdes_token(text):
                continue

            crop_box = item.get("bbox")
            if crop_box and len(crop_box) == 4:
                full_x1 = (x_offset + crop_box[0]) / float(img_w)
                full_y1 = crop_box[1] / float(img_h)
                full_x2 = (x_offset + crop_box[2]) / float(img_w)
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

        print("[INFO] Extracted " + str(len(extracted_items)) + " candidate BOM items on page " + str(page_number))
        return extracted_items


class BOMParser:
    """ BOM parser that dynamically isolates columns, coalesces split tokens, and expands ranges."""

    def __init__(self, min_col_width=150, min_gutter_width=40):
        """ Initialize parser configuration.

        Args:
          - min_col_width (int) : Minimum pixel width for a candidate column.
          - min_gutter_width (int) : Minimum whitespace gutter width.
        Returns: None.
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


# Backward compatibility aliases
DynamicBOMParser = BOMParser