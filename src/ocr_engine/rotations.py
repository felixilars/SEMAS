"""
Orthogonal Text Rotation & Multi-Angle Recognition Module
==========================================================
Recognizes component labels across 4 orthogonal rotation angles (0, 90, 180, 270 deg) using semantic candidate scoring to recover vertical and inverted text without noise regression or aspect-ratio heuristics.
"""

import re
import cv2

from .post_corrector import split_refdes_and_spec

REFDES_SYNTAX_PATTERN = re.compile(r"^[A-Z]{1,3}\d{1,4}[A-Z]?$")

ORTHOGONAL_ROTATION_STEPS = [
    (0, None),
    (90, cv2.ROTATE_90_CLOCKWISE),
    (270, cv2.ROTATE_90_COUNTERCLOCKWISE),
    (180, cv2.ROTATE_180),
]

def score_ocr_candidate(text, conf, lexicon):
    """ Compute semantic quality score for an OCR candidate text.

    Args:
      - text (str) : Candidate recognized text string.
      - conf (float) : Raw OCR confidence score.
      - lexicon (set | list | None) : Dynamic manual lexicon of valid RefDes strings.
    Returns: Float score combining semantic validity and confidence.
    """
    if not text:
        return 0.0

    refdes, _ = split_refdes_and_spec(text)
    clean_ref = re.sub(r"[^A-Za-z0-9]", "", refdes).upper() if refdes else ""

    if not clean_ref:
        return 0.0

    # Tier 3: Direct match in manual lexicon D_BOM
    if lexicon and clean_ref in lexicon:
        return 3.0 + float(conf)

    # Tier 2: Valid electronics RefDes syntax
    if REFDES_SYNTAX_PATTERN.match(clean_ref):
        return 2.0 + float(conf)

    # Tier 1: Has both letters and digits (e.g. R 101 or noisy candidate)
    has_alpha = any(c.isalpha() for c in clean_ref)
    has_digit = any(c.isdigit() for c in clean_ref)
    if has_alpha and has_digit:
        return 1.0 + float(conf)

    # Tier 0: Single character or letters-only / digits-only noise
    if len(clean_ref) >= 2:
        return 0.2 + 0.1 * float(conf)

    return 0.0

def read_text_with_orthogonal_rotations(crop_img, ocr_model, lexicon=None, conf_thresh=0.75):
    """ Recognize text across orthogonal angles (0, 90, 180, 270 deg) with semantic ranking.

    Args:
      - crop_img (np.ndarray) : BGR image crop of component.
      - ocr_model (BaseOCREngine) : Loaded OCR engine instance.
      - lexicon (set | list | None) : Optional set of valid RefDes strings.
      - conf_thresh (float) : Minimum confidence for early exit.
    Returns: Tuple of (best_text, best_confidence, best_angle_deg).
    """
    if crop_img is None or crop_img.size == 0:
        return "", 0.0, 0

    # 1. First attempt: Normal 0 deg orientation
    text_0, conf_0 = ocr_model.read_text(crop_img)
    score_0 = score_ocr_candidate(text_0, conf_0, lexicon)

    # Early exit: If text matches lexicon perfectly, return immediately
    ref_0, _ = split_refdes_and_spec(text_0)
    clean_0 = re.sub(r"[^A-Za-z0-9]", "", ref_0).upper() if ref_0 else ""

    if lexicon and clean_0 in lexicon:
        return text_0, conf_0, 0

    # If no lexicon is provided, early exit on high-confidence RefDes syntax
    if not lexicon and score_0 >= 2.0 and conf_0 >= conf_thresh:
        return text_0, conf_0, 0

    # 2. Sweep remaining orthogonal angles: 90 CW, 270 CW (90 CCW), 180 deg
    best_text = text_0
    best_conf = conf_0
    best_score = score_0
    best_angle = 0

    for angle, rot_flag in ORTHOGONAL_ROTATION_STEPS[1:]:
        rotated_crop = cv2.rotate(crop_img, rot_flag)
        rot_text, rot_conf = ocr_model.read_text(rotated_crop)
        rot_score = score_ocr_candidate(rot_text, rot_conf, lexicon)

        if rot_score > best_score:
            best_text = rot_text
            best_conf = rot_conf
            best_score = rot_score
            best_angle = angle

            ref_rot, _ = split_refdes_and_spec(rot_text)
            clean_rot = re.sub(r"[^A-Za-z0-9]", "", ref_rot).upper() if ref_rot else ""

            # If rotated text matches lexicon perfectly, break early
            if lexicon and clean_rot in lexicon:
                break

            # If no lexicon provided, break early on high-confidence RefDes
            if not lexicon and rot_score >= 2.0 and rot_conf >= conf_thresh:
                break

    return best_text, best_conf, best_angle