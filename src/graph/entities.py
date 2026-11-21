"""
Data Model
==========
Pydantic v2 models of the recognition results: boxes in page-normalized coordinates, parts
list rows, occurrences of a RefDes in one view, and the graph that links the three views of
a manual.
"""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

VIEWS = ("bom", "schematic", "pcb")
STATUSES = ("auto", "review", "unresolved")

class BBox(BaseModel):
    """ Box in page-normalized coordinates [0, 1]."""

    x1: float
    y1: float
    x2: float
    y2: float

    @field_validator("x1", "y1", "x2", "y2")
    @classmethod
    def clamp(cls, v):
        """ Clamp to the page; crop remapping can overshoot by a pixel."""
        return min(1.0, max(0.0, float(v)))

    @model_validator(mode="after")
    def check_order(self):
        """ Refuse inverted corners."""
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("Inverted box: " + str([self.x1, self.y1, self.x2, self.y2]))
        return self

    @classmethod
    def from_pixels(cls, box, width, height):
        """ Normalize a pixel box.

        Args:
          - box (list) : [x1, y1, x2, y2] in pixels.
          - width (int) : Page width in pixels.
          - height (int) : Page height in pixels.
        Returns: BBox.
        """
        return cls(x1=box[0] / width, y1=box[1] / height, x2=box[2] / width, y2=box[3] / height)

    def to_pixels(self, width, height):
        """ Pixel box on a page of the given size.

        Args:
          - width (int) : Page width in pixels.
          - height (int) : Page height in pixels.
        Returns: [x1, y1, x2, y2] as rounded integers.
        """
        return [round(self.x1 * width), round(self.y1 * height), round(self.x2 * width), round(self.y2 * height)]

class BOMItem(BaseModel):
    """ One row of a parts list, for one RefDes."""

    ref_des: str = Field(..., min_length=1)
    raw_description: str = ""
    page_number: int = Field(..., ge=1)
    bbox: Optional[BBox] = None
    value: Optional[str] = None
    tolerance: Optional[str] = None
    part_number: Optional[str] = None

    @field_validator("ref_des")
    @classmethod
    def normalize_refdes(cls, v):
        """ Strip and uppercase the RefDes."""
        return v.strip().upper()

    @field_validator("raw_description")
    @classmethod
    def strip_description(cls, v):
        """ Strip the description."""
        return v.strip()

    @field_validator("value", "tolerance", "part_number")
    @classmethod
    def strip_spec(cls, v):
        """ Strip a specification; an empty one becomes None."""
        return v.strip() or None if v is not None else None

class Occurrence(BaseModel):
    """ A RefDes found at one place of one view."""

    ref_des: str = Field(..., min_length=1)
    view: str = Field(..., description="bom, schematic or pcb")
    page_number: int = Field(..., ge=1)
    bbox: BBox
    raw_text: str = Field(default="", description="Text read by OCR before correction")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = Field(default="auto", description="auto (linked), review (queued) or unresolved")
    candidates: List[str] = Field(default_factory=list, description="Lexicon candidates, best first")

    @field_validator("ref_des")
    @classmethod
    def normalize_refdes(cls, v):
        """ Strip and uppercase the RefDes."""
        return v.strip().upper()

    @field_validator("view")
    @classmethod
    def check_view(cls, v):
        """ Refuse an unknown view."""
        if v not in VIEWS:
            raise ValueError("Unknown view: " + str(v))
        return v

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        """ Refuse an unknown status."""
        if v not in STATUSES:
            raise ValueError("Unknown status: " + str(v))
        return v

class Entity(BaseModel):
    """ One component of the manual with its occurrences in each view."""

    ref_des: str
    value: Optional[str] = None
    tolerance: Optional[str] = None
    part_number: Optional[str] = None
    occurrences: Dict[str, List[Occurrence]] = Field(default_factory=lambda: {v: [] for v in VIEWS})

    @property
    def is_tri_sync(self):
        """ True when the component was found in the three views."""
        return all(self.occurrences[v] for v in VIEWS)

class ManualGraph(BaseModel):
    """ Recognition result of one manual."""

    manual_id: str
    device_model: str
    entities: Dict[str, Entity] = Field(default_factory=dict)
    review_queue: List[Occurrence] = Field(default_factory=list)
    unresolved: List[Occurrence] = Field(default_factory=list)

    def add_occurrence(self, occurrence):
        """ File an occurrence by its status: linked to its entity, queued, or unresolved.

        Args:
          - occurrence (Occurrence) : Occurrence to add.
        Returns: The Entity it joined, or None for a queued or unresolved occurrence.
        """
        if occurrence.status == "review":
            self.review_queue.append(occurrence)
            return None
        if occurrence.status == "unresolved":
            self.unresolved.append(occurrence)
            return None
        entity = self.entities.setdefault(occurrence.ref_des, Entity(ref_des=occurrence.ref_des))
        entity.occurrences[occurrence.view].append(occurrence)
        return entity

    def save_json(self, path):
        """ Write the graph to a JSON file.

        Args:
          - path (str | Path) : Destination file; its folder is created when missing.
        Returns: None.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load_json(cls, path):
        """ Read a graph from a JSON file.

        Args:
          - path (str | Path) : Graph file.
        Returns: ManualGraph.
        """
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
