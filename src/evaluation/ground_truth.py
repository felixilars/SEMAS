"""
Ground Truth Data Contract
==========================
Pydantic v2 models and loader for the per-manual ground truth files stored in
data/ground_truth/<manual_id>.json. Boxes are [x1, y1, x2, y2] in pixels of the
300 DPI page images; page numbers are 1-based.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

COMPONENT_TYPES = (
    "Resistor", "Capacitor", "Transistor", "Diode", "Integrated Circuit", "Inductor",
    "Potentiometer", "Transformer", "Fuse", "Switch", "Test Point", "Connector",
    "Display/LED", "Assembly", "Other",
)


def validate_box(box):
    """ Check a pixel box [x1, y1, x2, y2].

    Args:
      - box (list | None) : Box coordinates or None when the view is not annotated.
    Returns: The box as a list of floats, or None.
    Raises: ValueError for a wrong length, negative coordinates or inverted corners.
    """
    if box is None:
        return None
    if len(box) != 4:
        raise ValueError("Box must have 4 values, got " + str(len(box)))
    x1, y1, x2, y2 = [float(v) for v in box]
    if min(x1, y1, x2, y2) < 0.0:
        raise ValueError("Box has negative coordinates: " + str(box))
    if x2 < x1 or y2 < y1:
        raise ValueError("Box corners are inverted: " + str(box))
    return [x1, y1, x2, y2]


class ComponentGT(BaseModel):
    """ Ground truth of one component across the BOM, schematic and PCB views."""

    refdes: str = Field(..., min_length=1, description="Reference designator, e.g. R102")
    component_type: str = Field(..., description="One of COMPONENT_TYPES")
    value: Optional[str] = Field(default=None, description="Nominal value, e.g. 47k")
    tolerance: Optional[str] = Field(default=None, description="Tolerance, e.g. 5%")
    part_number: Optional[str] = Field(default=None, description="Manufacturer part number")
    page_bom: Optional[int] = Field(default=None, ge=1, description="BOM page")
    bbox_table: Optional[List[float]] = Field(default=None, description="Box of the BOM row")
    page_schema: Optional[int] = Field(default=None, ge=1, description="Schematic page")
    bbox_schema: Optional[List[float]] = Field(default=None, description="Box of the schematic label")
    rotation_schema: float = Field(default=0.0, description="Label rotation in degrees")
    page_pcb: Optional[int] = Field(default=None, ge=1, description="PCB page")
    bbox_pcb: Optional[List[float]] = Field(default=None, description="Box of the PCB silkscreen label")
    board_name: Optional[str] = Field(default=None, description="Physical board name")

    @field_validator("refdes")
    @classmethod
    def normalize_refdes(cls, v):
        """ Strip and uppercase the reference designator."""
        return v.strip().upper()

    @field_validator("component_type")
    @classmethod
    def check_component_type(cls, v):
        """ Reject component types outside the known list."""
        if v not in COMPONENT_TYPES:
            raise ValueError("Unknown component_type: " + str(v))
        return v

    @field_validator("bbox_table", "bbox_schema", "bbox_pcb")
    @classmethod
    def check_box(cls, v):
        """ Validate pixel boxes."""
        return validate_box(v)

    @field_validator("rotation_schema")
    @classmethod
    def check_rotation(cls, v):
        """ Only orthogonal rotations are annotated."""
        if float(v) not in (0.0, 90.0, 180.0, 270.0):
            raise ValueError("rotation_schema must be 0, 90, 180 or 270, got " + str(v))
        return float(v)

    @model_validator(mode="after")
    def check_page_box_pairs(self):
        """ A box without its page cannot be located."""
        for page_name, box_name in (("page_schema", "bbox_schema"), ("page_pcb", "bbox_pcb"), ("page_bom", "bbox_table")):
            if getattr(self, box_name) is not None and getattr(self, page_name) is None:
                raise ValueError(box_name + " is set but " + page_name + " is missing for " + self.refdes)
        return self

    @property
    def has_bom(self):
        """ True when the component is listed on a BOM page."""
        return self.page_bom is not None

    @property
    def has_schematic(self):
        """ True when the component is located on a schematic page."""
        return self.page_schema is not None and self.bbox_schema is not None

    @property
    def has_pcb(self):
        """ True when the component is located on a PCB page."""
        return self.page_pcb is not None and self.bbox_pcb is not None

    @property
    def is_tri_sync_candidate(self):
        """ True when the component is annotated in all three views."""
        return self.has_bom and self.has_schematic and self.has_pcb


class ManualGT(BaseModel):
    """ Ground truth of one service manual."""

    manual_id: str = Field(..., min_length=1, description="Manual identifier, e.g. Toshiba_SY_330")
    device_model: str = Field(..., min_length=1, description="Device name")
    total_components: int = Field(default=0, ge=0, description="Number of components (recomputed)")
    components: Dict[str, ComponentGT] = Field(default_factory=dict, description="Components keyed by RefDes")

    @model_validator(mode="after")
    def check_keys_and_count(self):
        """ Keys must equal the component RefDes; the count is recomputed."""
        for key, comp in self.components.items():
            if key.strip().upper() != comp.refdes:
                raise ValueError("Key '" + key + "' does not match refdes '" + comp.refdes + "'")
        self.total_components = len(self.components)
        return self

    def tri_sync_candidates(self):
        """ Components annotated in all three views.

        Returns: List of ComponentGT sorted by RefDes.
        """
        return [self.components[k] for k in sorted(self.components) if self.components[k].is_tri_sync_candidate]


def load_ground_truth(path):
    """ Load and validate a ground truth JSON file.

    Args:
      - path (str | Path) : JSON file.
    Returns: ManualGT instance.
    Raises: FileNotFoundError if the file is missing; pydantic.ValidationError if invalid.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError("Ground truth file not found: " + str(file_path))
    with open(file_path, "r", encoding="utf-8") as f:
        return ManualGT.model_validate(json.load(f))


def load_all_ground_truth(directory):
    """ Load every ground truth file of a directory.

    Args:
      - directory (str | Path) : Folder containing <manual_id>.json files.
    Returns: Dict mapping manual_id to ManualGT, sorted by manual_id.
    """
    manuals = {}
    for file_path in sorted(Path(directory).glob("*.json")):
        gt = load_ground_truth(file_path)
        manuals[gt.manual_id] = gt
    return manuals
