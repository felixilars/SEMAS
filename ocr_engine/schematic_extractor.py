"""
Schematic Component OCR Extractor Module
========================================
Extracts and recognizes component reference designator labels and attached specifications
from schematic diagram bounding boxes using multi-angle orthogonal text orientation sweeps.
"""

from pathlib import Path
import json
import re
import sys
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from ocr_engine.base import BaseOCREngine
from ocr_engine.rotations import read_text_with_orthogonal_rotations
from ocr_engine.post_corrector import split_refdes_and_spec

class SchematicOCRExtractor:
    """ Extracts component labels from schematic diagram image regions."""

    def __init__(self, ocr_engine=None, padding=4, conf_thresh=0.75):
        """ Initialize schematic extractor configuration.

        Args:
          - ocr_engine (BaseOCREngine | None) : OCR engine instance.
          - padding (int) : Pixel padding added around bounding boxes.
          - conf_thresh (float) : Confidence threshold for early rotation exit.
        """
        self.ocr_engine = ocr_engine
        self.padding = int(padding)
        self.conf_thresh = float(conf_thresh)

    def crop_box(self, image, bbox):
        """ Crop sub-region from image with boundary safety clamping and padding.

        Args:
          - image (np.ndarray) : Source image array.
          - bbox (list | tuple) : Bounding box coordinates [x1, y1, x2, y2].
        Returns: Cropped pixel array, or None if coordinates are invalid.
        """
        if image is None or image.size == 0 or len(bbox) < 4:
            return None

        img_h, img_w = image.shape[:2]
        x1, y1, x2, y2 = [int(round(coord)) for coord in bbox[:4]]

        # Coordinate order validation
        if x2 < x1 or y2 < y1:
            return None

        # Apply padding and clamp to image dimensions
        safe_x1 = max(0, x1 - self.padding)
        safe_y1 = max(0, y1 - self.padding)
        safe_x2 = min(img_w, x2 + self.padding)
        safe_y2 = min(img_h, y2 + self.padding)

        if safe_x2 <= safe_x1 or safe_y2 <= safe_y1:
            return None

        return image[safe_y1:safe_y2, safe_x1:safe_x2].copy()

    def extract_label(self, image, bbox, lexicon=None):
        """ Crop component region and recognize text label across orthogonal rotations.

        Args:
          - image (np.ndarray) : Source schematic page image.
          - bbox (list | tuple) : Component bounding box [x1, y1, x2, y2].
          - lexicon (set | list | None) : Optional set of valid RefDes tokens.
        Returns: Dictionary containing recognized text, refdes, spec, confidence, and rotation angle.
        """
        crop = self.crop_box(image, bbox)
        if crop is None:
            return {
                "raw_text": "",
                "ref_des": "",
                "spec_value": None,
                "confidence": 0.0,
                "rotation_deg": 0,
                "bbox": list(bbox),
            }

        if self.ocr_engine is None:
            from ocr_engine import get_ocr_engine
            self.ocr_engine = get_ocr_engine("paddleocr")

        best_text, best_conf, best_angle = read_text_with_orthogonal_rotations(
            crop,
            self.ocr_engine,
            lexicon=lexicon,
            conf_thresh=self.conf_thresh,
        )

        clean_ref, spec_val = split_refdes_and_spec(best_text)

        return {
            "raw_text": str(best_text).strip(),
            "ref_des": str(clean_ref).strip().upper(),
            "spec_value": str(spec_val).strip() if spec_val else None,
            "confidence": round(float(best_conf), 4),
            "rotation_deg": int(best_angle),
            "bbox": list(bbox),
        }

    def extract_schematic_components(self, image, candidate_boxes, lexicon=None):
        """ Process all candidate component boxes across a schematic page.

        Args:
          - image (np.ndarray) : Full schematic page image.
          - candidate_boxes (list) : List of bounding boxes [x1, y1, x2, y2].
          - lexicon (set | list | None) : Optional dynamic manual lexicon.
        Returns: List of recognized component record dictionaries.
        """
        print("[INFO] Processing " + str(len(candidate_boxes)) + " candidate bounding boxes on schematic")
        results = []

        for idx, box in enumerate(candidate_boxes):
            record = self.extract_label(image, box, lexicon=lexicon)
            record["box_index"] = idx
            results.append(record)

        valid_count = sum(1 for r in results if r["ref_des"])
        print("[INFO] Recognized " + str(valid_count) + "/" + str(len(candidate_boxes)) + " component labels")
        return results

    def export_detections(self, detections, output_path):
        """ Serialize component detections to JSON format.

        Args:
          - detections (list) : List of component record dictionaries.
          - output_path (Path | str) : Target JSON file location.
        Returns: None.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(detections, f, indent=2)

        print("[INFO] Exported schematic detections to: " + str(out_file))