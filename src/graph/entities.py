"""
Entities & Data Contracts Module
=================================
Provides lightweight foundational entities for representing bounding box geometry and extracted Bill of Materials (BOM) tabular entries.
"""

class BBox:
    """ Normalized bounding box representation in [0.0, 1.0] coordinate space."""

    def __init__(self, x1, y1, x2, y2):
        """ Initialize normalized bounding box with coordinate validation.

        Args:
          - x1 (float) : Normalized left boundary [0.0, 1.0].
          - y1 (float) : Normalized top boundary [0.0, 1.0].
          - x2 (float) : Normalized right boundary [0.0, 1.0].
          - y2 (float) : Normalized bottom boundary [0.0, 1.0].
        """
        # Enforce boundary clamp and ordering
        self.x1 = max(0.0, min(1.0, float(x1)))
        self.y1 = max(0.0, min(1.0, float(y1)))
        self.x2 = max(0.0, min(1.0, float(x2)))
        self.y2 = max(0.0, min(1.0, float(y2)))

        if self.x2 < self.x1:
            raise ValueError("Invalid bounding box: x2 (" + str(self.x2) + ") < x1 (" + str(self.x1) + ")")
        if self.y2 < self.y1:
            raise ValueError("Invalid bounding box: y2 (" + str(self.y2) + ") < y1 (" + str(self.y1) + ")")

    def to_pixel(self, img_width, img_height):
        """ Convert normalized coordinates to absolute integer pixel coordinates.

        Args:
          - img_width (int) : Width of the source image in pixels.
          - img_height (int) : Height of the source image in pixels.
        Returns: List of four integers [px_x1, px_y1, px_x2, px_y2].
        """
        return [
            int(round(self.x1 * img_width)),
            int(round(self.y1 * img_height)),
            int(round(self.x2 * img_width)),
            int(round(self.y2 * img_height)),
        ]

    def compute_area(self):
        """ Compute normalized rectangular area """
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    def to_dict(self):
        """ Serialize bounding box to dictionary format """
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
        }

class BOMItem:
    """ Basic representation of an individual component record in a BOM table."""

    def __init__(self, ref_des, raw_description, page_number, bbox=None, value=None, tolerance=None, part_number=None):
        """ Initialize a single BOM item record.

        Args:
          - ref_des (str) : Extracted reference designator (e.g. 'R101').
          - raw_description (str) : Raw textual specification or description.
          - page_number (int) : 1-based index of the source document page.
          - bbox (BBox or None) : Normalized bounding box if available.
          - value (str or None) : Electrical rating or value (e.g. '47k', '0.047uF').
          - tolerance (str or None) : Rating tolerance (e.g. '5%', '+/-10%').
          - part_number (str or None) : Manufacturer part number or commercial code.
        """
        self.ref_des = str(ref_des).strip().upper()
        self.raw_description = str(raw_description).strip()
        self.page_number = int(page_number)
        self.bbox = bbox
        self.value = str(value).strip() if value else None
        self.tolerance = str(tolerance).strip() if tolerance else None
        self.part_number = str(part_number).strip() if part_number else None

    def to_dict(self):
        """ Serialize BOM item to clean dictionary structure."""
        return {
            "ref_des": self.ref_des,
            "raw_description": self.raw_description,
            "page_number": self.page_number,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "value": self.value,
            "tolerance": self.tolerance,
            "part_number": self.part_number,
        }