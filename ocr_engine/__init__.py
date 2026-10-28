"""
OCR Engine Package
==================
Modular OCR integration library for electronic service manual recognition. Provides PaddleOCREngine and the factory function `get_ocr_engine`.
"""

from .base import BaseOCREngine
from .paddle_ocr import PaddleOCREngine

_ENGINE_CACHE = {}

def get_ocr_engine(engine_name="paddleocr", use_angle_cls=True, lang="en", **kwargs):
    """ Factory function to retrieve or instantiate a cached OCR engine.

    Args:
      - engine_name (str) : OCR engine identifier ('paddleocr', 'easyocr', 'tesseract').
      - use_angle_cls (bool) : Text orientation classification flag.
      - lang (str) : Target recognition language code.
      - kwargs (dict) : Extra parameters passed to the engine.
    Returns: Instance conforming to BaseOCREngine.
    """
    normalized_name = engine_name.lower().strip()
    cache_key = normalized_name + "_" + str(use_angle_cls) + "_" + str(lang) + "_" + str(sorted(kwargs.items()))

    if cache_key not in _ENGINE_CACHE:
        if normalized_name == "paddleocr":
            _ENGINE_CACHE[cache_key] = PaddleOCREngine(use_angle_cls, lang)

    return _ENGINE_CACHE[cache_key]

def read_text(crop_img, engine="paddleocr"):
    """ Convenience helper to read text from an image crop using a selected engine.

    Args:
      - crop_img (np.ndarray) : Image region array in BGR or Grayscale.
      - engine (BaseOCREngine | str) : Engine instance or name string.
    Returns: Tuple of recognized text and confidence score.
    """
    if isinstance(engine, BaseOCREngine):
        ocr_instance = engine
    elif isinstance(engine, str):
        ocr_instance = get_ocr_engine(engine)
    else:
        ocr_instance = get_ocr_engine("paddleocr")

    return ocr_instance.read_text(crop_img)


from .post_corrector import (
    CorrectionResult,
    PostCorrector,
    compute_weighted_levenshtein,
    split_refdes_and_spec,
)
from .rotations import (
    read_text_with_orthogonal_rotations,
    score_ocr_candidate,
)
from .schematic_extractor import SchematicOCRExtractor

__all__ = [
    "BaseOCREngine",
    "PaddleOCREngine",
    "get_ocr_engine",
    "read_text",
    "PostCorrector",
    "CorrectionResult",
    "split_refdes_and_spec",
    "compute_weighted_levenshtein",
    "read_text_with_orthogonal_rotations",
    "score_ocr_candidate",
    "SchematicOCRExtractor",
]