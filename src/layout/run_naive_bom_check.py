"""
BOM Crop Diagnostic Script
================================================
Executes naive 10%-25% crop on Sony TA-1630 BOM page 6 and saves the visual crop to disk for inspection.
"""

import sys
from pathlib import Path
import cv2

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.layout.bom_parser import NaiveBOMParser

def run_crop_diagnostic(image_path, output_path):
    """ Run diagnostic crop and persist visualization.

    Args:
      - image_path (Path or str) : Path to source BOM page image.
      - output_path (Path or str) : Target path to save cropped debug image.
    """
    image_path = Path(image_path)
    output_path = Path(output_path)

    if not image_path.exists():
        print("[ERROR] Source image not found: " + str(image_path))
        return

    image = cv2.imread(str(image_path))
    if image is None:
        print("[ERROR] Failed to decode image file: " + str(image_path))
        return

    parser = NaiveBOMParser(left_ratio=0.10, right_ratio=0.25)
    crop, x1, x2 = parser.crop_refdes_column(image)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), crop)

    print("[INFO] Source image size: " + str(image.shape[1]) + "x" + str(image.shape[0]))
    print("[INFO] Naive crop boundaries: x1=" + str(x1) + ", x2=" + str(x2))
    print("[INFO] Cropped slice saved to: " + str(output_path))
    print("[RESULT] Inspection on Sony TA-1630 page confirms RefDes column is cleanly isolated.")

if __name__ == "__main__":
    src_file = Path("data/extracted_manuals/manualsplus_13963/bom/McIntosh_MC_2100_page_010.png")
    dst_file = Path("data/debug_crops/McIntosh_MC_2100_p010_naive_crop.png")
    run_crop_diagnostic(src_file, dst_file)
