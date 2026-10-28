"""
Dynamic Vertical Gutters & Column Segmentation Module
=============================================================
Detects vertical whitespace gutters between text columns using Vertical Projection Histograms, automatically segmenting single-column, right-aligned, and multi-column BOM layouts without hardcoded margin percentages.
"""

from pathlib import Path
import cv2
import numpy as np

def compute_vertical_projection(image):
    """ Compute 1D vertical ink projection profile across image width.

    Args:
      - image (np.ndarray) : Source BGR or grayscale image array.
    Returns: 1D numpy array of summed ink pixel intensities per column x.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Invert binary threshold: ink/text becomes 255 (white), clean paper becomes 0 (black)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Sum along Y axis (axis=0) to measure ink mass for each vertical column x
    projection = np.sum(binary, axis=0)
    return projection


def detect_vertical_gutters(image, min_gutter_width=40, ink_threshold_ratio=0.005):
    """ Detect vertical whitespace gutters (valleys of near-zero ink density).

    Args:
      - image (np.ndarray) : Source image array.
      - min_gutter_width (int) : Minimum width in pixels to qualify as a column separator.
      - ink_threshold_ratio (float) : Max ratio of column height considered blank white space.
    Returns: List of tuple boundaries [(gutter_start_x, gutter_end_x), ...].
    """
    proj = compute_vertical_projection(image)
    height = image.shape[0]

    # Threshold ink mass below which a vertical line is considered empty whitespace
    max_blank_ink = height * 255 * float(ink_threshold_ratio)
    is_whitespace = proj < max_blank_ink

    gutters = []
    in_gutter = False
    start_x = 0

    for x, blank in enumerate(is_whitespace):
        if blank and not in_gutter:
            in_gutter = True
            start_x = x
        elif not blank and in_gutter:
            in_gutter = False
            gutter_width = x - start_x
            if gutter_width >= min_gutter_width:
                gutters.append((start_x, x))

    # Catch trailing gutter reaching the right page boundary
    if in_gutter and (len(is_whitespace) - start_x) >= min_gutter_width:
        gutters.append((start_x, len(is_whitespace)))

    return gutters


def find_column_slices(image, min_column_width=150, min_gutter_width=40):
    """ Segment document page into active content column slices based on gutters.

    Args:
      - image (np.ndarray) : Source document image.
      - min_column_width (int) : Minimum width for a valid text column.
      - min_gutter_width (int) : Minimum whitespace width between columns.
    Returns: List of column coordinate tuples [(x_start, x_end), ...].
    """
    width = image.shape[1]
    gutters = detect_vertical_gutters(image, min_gutter_width=min_gutter_width)

    # Invert gutters to obtain content column boundaries
    content_columns = []
    current_x = 0

    for g_start, g_end in gutters:
        col_width = g_start - current_x
        if col_width >= min_column_width:
            content_columns.append((current_x, g_start))
        current_x = g_end

    # Trailing content column after the last gutter
    if (width - current_x) >= min_column_width:
        content_columns.append((current_x, width))

    return content_columns
