"""
Dynamic Gutters Visual Diagnostic Script (Day 4)
================================================
Applies vertical projection gutter detection across Sony, McIntosh, and Toshiba,drawing green boundaries around detected columns and saving debug visualizations.
"""

import sys
from pathlib import Path
import cv2

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.layout.gutter_detector import find_column_slices

def visualize_detected_columns(image_path, output_dir):
    """ Detect columns and draw green bounding boxes on the full page image.

    Args:
      - image_path (Path) : Path to source BOM page image.
      - output_dir (Path) : Target output directory for visualizations.
    """
    if not image_path.exists():
        print("[WARN] File not found: " + str(image_path))
        return

    image = cv2.imread(str(image_path))
    if image is None:
        print("[ERROR] Cannot read image: " + str(image_path))
        return

    h, w = image.shape[:2]
    columns = find_column_slices(image, min_column_width=150, min_gutter_width=40)

    vis_img = image.copy()
    for idx, (x1, x2) in enumerate(columns):
        # Draw translucent green rectangle over each detected column
        overlay = vis_img.copy()
        cv2.rectangle(overlay, (x1, 0), (x2, h), (0, 255, 0), -1)
        cv2.addWeighted(overlay, 0.15, vis_img, 0.85, 0, vis_img)

        # Draw solid boundary lines
        cv2.line(vis_img, (x1, 0), (x1, h), (0, 200, 0), 3)
        cv2.line(vis_img, (x2, 0), (x2, h), (0, 200, 0), 3)

        # Put column label text
        label = "Col " + str(idx + 1) + " [" + str(x1) + ":" + str(x2) + "]"
        cv2.putText(vis_img, label, (x1 + 15, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 150, 0), 3)

    out_file = output_dir / ("gutters_" + image_path.stem + ".png")
    output_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_file), vis_img)

    print("[INFO] " + str(image_path.name) + ": Detected " + str(len(columns)) + " column(s)")
    for idx, (x1, x2) in enumerate(columns):
        ratio_x1 = round(x1 / float(w), 3)
        ratio_x2 = round(x2 / float(w), 3)
        print("  - Column " + str(idx + 1) + ": px=[" + str(x1) + ":" + str(x2) + "], ratio=[" + str(ratio_x1) + ":" + str(ratio_x2) + "]")
    print("[INFO] Saved visualization to: " + str(out_file))


def main():
    """ Run visual column detection across the three diagnostic manuals."""
    print("[INFO] RUNNING DYNAMIC GUTTERS DIAGNOSTIC ACROSS 3 MANUALS")
    out_dir = Path("data/debug_crops")
    samples = [
        Path("data/extracted_manuals/Sony-TA-1630-Service-Manual/bom/Sony_TA_1630_page_009.png"),
        Path("data/extracted_manuals/manualsplus_13963/bom/McIntosh_MC_2100_page_010.png"),
        Path("data/extracted_manuals/Toshiba-SY-330-Service-Manual/bom/Toshiba_SY_330_page_007.png"),
    ]

    for p in samples:
        print("----------------------------------------------------------------------")
        visualize_detected_columns(p, out_dir)

    print("[RESULT] Dynamic Gutters inspection complete. Check images in data/debug_crops")

if __name__ == "__main__":
    main()
