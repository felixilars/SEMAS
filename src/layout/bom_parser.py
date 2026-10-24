"""
BOM Table Parser Module
=====================================================
Initial experimental implementation for extracting component references from tabular Bill of Materials pages by cropping a hardcoded horizontal slice observed on Sony TA-1630 service manuals.
"""

import re
import numpy as np
import sys

from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.graph.entities import BBox, BOMItem

class NaiveBOMParser:
    """ Naive parser relying on hardcoded horizontal percentage margins."""

    def __init__(self, left_ratio=0.10, right_ratio=0.25):
        """ Initialize parser with empirical margin boundaries.

        Args:
          - left_ratio (float) : Left margin ratio of page width (default: 0.10).
          - right_ratio (float) : Right margin ratio of page width (default: 0.25).
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

        print("[INFO] Running naive OCR on cropped column: width=" + str(cropped_img.shape[1]) + ", height=" + str(cropped_img.shape[0]))

        # ocr_engine returns list of dicts: [{"text": str, "bbox": [x1, y1, x2, y2], "confidence": float}]
        raw_detections = ocr_engine.recognize(cropped_img)
        extracted_items = []

        for item in raw_detections:
            text = str(item.get("text", "")).strip()
            if not self.is_valid_refdes_token(text):
                continue

            crop_box = item.get("bbox")  # Pixel coordinates in cropped image: [cx1, cy1, cx2, cy2]
            if crop_box and len(crop_box) == 4:
                # Map cropped x coordinates back to full-page coordinate space
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
