"""
Base OCR Engine Interface
=========================
Defines the standard abstract contract for all optical character recognition engines.
"""

from abc import ABC, abstractmethod


class BaseOCREngine(ABC):
    """ Abstract base class defining the contract for all optical character recognition engines."""

    @abstractmethod
    def read_text(self, crop_img):
        """ Recognize text and return average confidence score from a cropped image array.

        Args:
          - crop_img (np.ndarray) : Image region in BGR or Grayscale format.
        Returns: Tuple of (recognized_text, confidence_score). Returns ("", 0.0) if no text is detected.
        """
        pass

    @abstractmethod
    def extract_text_boxes(self, image_np):
        """ Extract bounding boxes, text tokens, and confidence scores from an uncropped image.

        Args:
          - image_np (np.ndarray) : Full or sub-region image array.
        Returns: List of dicts [{"text": str, "bbox": [x1, y1, x2, y2], "confidence": float}, ...].
        """
        pass

