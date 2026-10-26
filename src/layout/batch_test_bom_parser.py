"""
Batch BOM Crop Inspection
===========================
Applies the NaiveBOMParser margin cropping across multiple manual models (Sony, McIntosh, Toshiba) and exports visual crops for manual verification.
"""

from pathlib import Path
import cv2
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.layout.bom_parser import NaiveBOMParser


def process_manual_crop(image_path, output_dir, parser):
    """ Load a single BOM page image, crop the RefDes column, and save output.

    Args:
      - image_path (Path) : Path to source BOM page image.
      - output_dir (Path) : Directory to save cropped image.
      - parser (NaiveBOMParser) : Configured parser instance.
    Returns: Path to saved crop image or None on failure.
    """
    if not image_path.exists():
        print("[WARN] File not found: " + str(image_path))
        return None

    image = cv2.imread(str(image_path))
    if image is None:
        print("[ERROR] Cannot read image: " + str(image_path))
        return None

    # Crop vertical slice using parser margin bounds
    crop, x1, x2 = parser.crop_refdes_column(image)

    # Build clear output filename
    manual_name = image_path.parent.parent.name
    out_filename = manual_name + "_" + image_path.stem + "_crop.png"
    out_path = output_dir / out_filename

    output_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), crop)

    print("[INFO] Processed: " + str(image_path.name))
    print("[INFO] Source size: " + str(image.shape[1]) + "x" + str(image.shape[0]) + " | Crop slice: [" + str(x1) + ":" + str(x2) + "]")
    print("[INFO] Saved slice to: " + str(out_path))
    return out_path

def main():
    parser = NaiveBOMParser(left_ratio=0.10, right_ratio=0.25)
    debug_dir = Path("data/debug_crops")

    test_samples = [
        Path("data/extracted_manuals/Sony-TA-1630-Service-Manual/bom/Sony_TA_1630_page_009.png"),
        Path("data/extracted_manuals/manualsplus_13963/bom/McIntosh_MC_2100_page_010.png"),
        Path("data/extracted_manuals/Toshiba-SY-330-Service-Manual/bom/Toshiba_SY_330_page_007.png"),
    ]

    processed_count = 0
    for sample_path in test_samples:
        print("----------------------------------------------------------------------")
        res = process_manual_crop(sample_path, debug_dir, parser)
        if res:
            processed_count = processed_count + 1

    print("\n\n")
    print("[INFO] Completed processing " + str(processed_count) + " test pages.")
    print("[INFO] Inspect output images in: " + str(debug_dir))

if __name__ == "__main__":
    main()
