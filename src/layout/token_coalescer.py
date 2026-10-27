"""
Horizontal Token Coalescing Module
==================================
Merges severed prefix-numeric OCR bounding box pairs (e.g. 'R' + '101' -> 'R101') caused by wide font kerning on vintage technical manuals.
"""

from pathlib import Path
import re

# Recognized electronic reference designator prefixes
PREFIX_CANDIDATES = (
    "R", "C", "Q", "TR", "D", "IC", "VR", "RV", "L", "T", "F", "SW", "TP", "J", "P"
)

def is_prefix_token(text):
    """ Check whether a token represents an isolated component letter prefix.

    Args:
      - text (str) : Candidate token text.
    Returns: True if token matches a valid component prefix, False otherwise.
    """
    cleaned = str(text).strip().upper()
    return cleaned in PREFIX_CANDIDATES

def is_numeric_index_token(text):
    """ Check whether a token represents an isolated numeric component index.

    Args:
      - text (str) : Candidate token text.
    Returns: True if token matches a numeric component index, False otherwise.
    """
    cleaned = str(text).strip()
    # Reject tokens ending with electrical unit multipliers or units
    if re.search(r"[kKmMuUvVwWfF%]$", cleaned):
        return False
    return bool(re.match(r"^\d{1,4}[A-DLR]?$", cleaned, re.IGNORECASE))

def coalesce_adjacent_tokens(tokens, max_x_gap=40, max_y_drift=12):
    """ Horizontally merge adjacent severed OCR tokens located on the same row.

    Args:
      - tokens (list) : List of detection dicts: [{'text': str, 'bbox': [x1,y1,x2,y2], 'confidence': float}].
      - max_x_gap (int) : Maximum horizontal pixel distance between boxes to permit merging.
      - max_y_drift (int) : Maximum vertical center drift between boxes on the same line.
    Returns: New list of coalesced detection dictionaries.
    """
    if not tokens:
        return []

    # Sort tokens top-to-bottom (Y), then left-to-right (X)
    sorted_tokens = sorted(tokens, key=lambda b: (b.get("bbox", [0, 0, 0, 0])[1], b.get("bbox", [0, 0, 0, 0])[0]))

    coalesced = []
    skip_indices = set()

    for i in range(len(sorted_tokens)):
        if i in skip_indices:
            continue

        curr = sorted_tokens[i]
        curr_text = str(curr.get("text", "")).strip()
        curr_box = curr.get("bbox", [0, 0, 0, 0])
        curr_conf = float(curr.get("confidence", 1.0))

        # Check internal space: e.g. OCR returned 'R 101' inside a single box
        curr_text = re.sub(r"^([A-Za-z]{1,3})\s+(\d{1,4}[A-Za-z]?)(?=\s|$)", r"\1\2", curr_text)

        # Look ahead to see if the immediate next token is its severed numeric pair
        if i + 1 < len(sorted_tokens):
            nxt = sorted_tokens[i + 1]
            nxt_text = str(nxt.get("text", "")).strip()
            nxt_box = nxt.get("bbox", [0, 0, 0, 0])
            nxt_conf = float(nxt.get("confidence", 1.0))

            x_gap = nxt_box[0] - curr_box[2]
            curr_y_center = (curr_box[1] + curr_box[3]) / 2.0
            nxt_y_center = (nxt_box[1] + nxt_box[3]) / 2.0
            y_drift = abs(curr_y_center - nxt_y_center)
            
            """
            Check merging conditions:
                1. Bounding boxes are horizontally adjacent within max_x_gap
                2. Both boxes sit on approximately the same horizontal baseline
                3. Left is prefix ('R') and Right is numeric ('101')
            """
            if 0 <= x_gap <= max_x_gap and y_drift <= max_y_drift:
                if is_prefix_token(curr_text) and is_numeric_index_token(nxt_text):
                    merged_text = curr_text + nxt_text
                    merged_box = [
                        curr_box[0],
                        min(curr_box[1], nxt_box[1]),
                        nxt_box[2],
                        max(curr_box[3], nxt_box[3]),
                    ]
                    merged_conf = (curr_conf + nxt_conf) / 2.0

                    print("[INFO] Merged split tokens: '" + curr_text + "' + '" + nxt_text + "' -> '" + merged_text + "'")

                    coalesced.append({
                        "text": merged_text,
                        "bbox": merged_box,
                        "confidence": merged_conf,
                    })
                    skip_indices.add(i + 1)
                    continue

        # If not merged, append current token as is
        coalesced.append({
            "text": curr_text,
            "bbox": curr_box,
            "confidence": curr_conf,
        })

    return coalesced