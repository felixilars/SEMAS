"""
PaddleOCR Engine Wrapper
========================
High-precision OCR integration using PaddleOCR (PP-OCRv4 / PP-OCRv6 with Text Angle Classification)"""

import logging
import os
import numpy as np

# Suppress known PaddlePaddle 3.x oneDNN/PIR conflicts on CPU
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from .base import BaseOCREngine

logger = logging.getLogger("PaddleOCREngine")
class PaddleOCREngine(BaseOCREngine):
    """ PaddleOCR Engine wrapper with angle classification support."""

    def __init__(self, use_angle_cls, lang):
        """ Initialize the PaddleOCR engine.

        Args:
          - use_angle_cls (bool) : Whether to activate angle classifier.
          - lang (str) : Language code for optical recognition.
        Returns: None.
        """
        self.use_angle_cls = use_angle_cls
        self.lang = lang
        self._model = None

    def _get_model(self):
        """ Lazy loader for PaddleOCR model instance with compatibility handling.

        Returns: Initialized PaddleOCR model instance.
        """
        if self._model is None:
            try:
                from paddleocr import PaddleOCR
                logger.info("Initializing PaddleOCR (use_angle_cls=%s, lang=%s)...", self.use_angle_cls, self.lang)
                # Initialize PaddleOCR: disable doc unwarping to prevent coordinate distortions on flat scans
                try:
                    self._model = PaddleOCR(
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=self.use_angle_cls,
                        lang=self.lang,
                        enable_mkldnn=False,
                    )
                except (ValueError, TypeError):
                    try:
                        self._model = PaddleOCR(
                            use_doc_orientation_classify=False,
                            use_doc_unwarping=False,
                            use_textline_orientation=self.use_angle_cls,
                            lang=self.lang,
                        )
                    except (ValueError, TypeError):
                        self._model = PaddleOCR(
                            use_angle_cls=self.use_angle_cls,
                            lang=self.lang,
                        )
            except ImportError as exc:
                raise ImportError(
                    "PaddleOCR is not installed. Run: pip install paddlepaddle paddleocr"
                ) from exc
        return self._model

    def read_text(self, crop_img):
        """ Recognize text and compute average confidence from a cropped image array.

        Args:
          - crop_img (np.ndarray) : Image region in BGR format.
        Returns: Tuple of (recognized_text, confidence_score).
        """
        if crop_img is None or crop_img.size == 0:
            return "", 0.0

        model = self._get_model()
        try:
            results = model.ocr(crop_img)
        except Exception:
            return "", 0.0

        if not results:
            return "", 0.0

        text_tokens = []
        confidences = []

        for item in results:
            if isinstance(item, dict):
                # PaddleOCR 3.x format
                texts = item.get("rec_texts", [])
                scores = item.get("rec_scores", [])
                for t, c in zip(texts, scores):
                    clean = str(t).strip()
                    if clean:
                        text_tokens.append(clean)
                        confidences.append(float(c))
            elif isinstance(item, (list, tuple)):
                # PaddleOCR 2.x format
                for line in item:
                    if isinstance(line, (list, tuple)) and len(line) >= 2 and len(line[1]) >= 2:
                        token_str = str(line[1][0]).strip()
                        conf_val = float(line[1][1])
                        if token_str:
                            text_tokens.append(token_str)
                            confidences.append(conf_val)

        if not text_tokens:
            return "", 0.0

        combined_text = " ".join(text_tokens).strip()
        avg_confidence = float(np.mean(confidences)) if confidences else 0.0
        return combined_text, avg_confidence

    def extract_text_boxes(self, image_np):
        """ Extract bounding boxes, text strings, and confidence from an image.

        Args:
          - image_np (np.ndarray) : Target image array.
        Returns: List of dicts containing text, bbox [x1, y1, x2, y2], and confidence.
        """
        if image_np is None or image_np.size == 0:
            return []

        model = self._get_model()
        try:
            results = model.ocr(image_np)
        except Exception:
            return []

        boxes_out = []
        if not results:
            return boxes_out

        for item in results:
            if isinstance(item, dict):
                # PaddleOCR 3.x format
                boxes = item.get("rec_boxes", [])
                texts = item.get("rec_texts", [])
                scores = item.get("rec_scores", [])
                for b, t, c in zip(boxes, texts, scores):
                    clean = str(t).strip()
                    if clean and len(b) >= 4:
                        boxes_out.append({
                            "text": clean,
                            "bbox": [int(b[0]), int(b[1]), int(b[2]), int(b[3])],
                            "confidence": float(c),
                        })
            elif isinstance(item, (list, tuple)):
                # PaddleOCR 2.x format
                for line in item:
                    if isinstance(line, (list, tuple)) and len(line) >= 2:
                        poly, (text, conf) = line[0], line[1]
                        xs = [pt[0] for pt in poly]
                        ys = [pt[1] for pt in poly]
                        boxes_out.append({
                            "text": str(text).strip(),
                            "bbox": [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))],
                            "confidence": float(conf),
                        })

        return boxes_out