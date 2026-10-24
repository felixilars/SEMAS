"""
Unit Tests for Batch BOM Cropping
=================================
Ensures batch processing handles multiple image sizes without crashing.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))

from src.layout.bom_parser import NaiveBOMParser
from src.layout.batch_test_bom_parser import process_manual_crop

def test_process_manual_crop_creates_file(tmp_path):
    """ Verify process_manual_crop successfully writes image to target directory."""
    # Create synthetic test image (1000x2000)
    test_img = np.full((1000, 2000, 3), 255, dtype=np.uint8)
    sample_dir = tmp_path / "manual_test" / "bom"
    sample_dir.mkdir(parents=True)
    sample_file = sample_dir / "page_001.png"

    import cv2
    cv2.imwrite(str(sample_file), test_img)

    parser = NaiveBOMParser(left_ratio=0.10, right_ratio=0.25)
    out_dir = tmp_path / "output_crops"

    saved_path = process_manual_crop(sample_file, out_dir, parser)

    assert saved_path is not None
    assert saved_path.exists()
    assert saved_path.stat().st_size > 0
