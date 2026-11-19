"""
Manual Registry
===============
Single place for the facts about each service manual: identifier, PDF and page folder
name, device name, dev/test split and hand-sorted page table. They live in
data/manifests/manuals.json, so that code never names a manual.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_FILE = PROJECT_ROOT / "data" / "manifests" / "manuals.json"
RAW_MANUALS_DIR = PROJECT_ROOT / "data" / "raw_manuals"
EXTRACTED_MANUALS_DIR = PROJECT_ROOT / "data" / "extracted_manuals"
PAGE_ROLES = ("bom", "schematic", "pcb")
SPLITS = ("train", "dev", "test", "unused")


class ManualEntry(BaseModel):
    """ Registry entry of one service manual."""

    manual_id: str = Field(..., min_length=1, description="Identifier used in file names, e.g. Toshiba_SY_330")
    folder: str = Field(..., min_length=1, description="PDF file stem and name of the page folder")
    device_model: str = Field(..., min_length=1, description="Device name written in reports")
    split: str = Field(..., description="train, dev, test or unused")
    pages: Dict[str, List[int]] = Field(default_factory=dict, description="Hand-sorted 1-based pages per role")
    note: Optional[str] = Field(default=None, description="Free remark about the manual")

    @field_validator("split")
    @classmethod
    def check_split(cls, value):
        """ Refuse an unknown split."""
        if value not in SPLITS:
            raise ValueError("Unknown split '" + str(value) + "', expected one of " + ", ".join(SPLITS))
        return value

    @field_validator("pages")
    @classmethod
    def check_pages(cls, value):
        """ Refuse unknown roles and pages below 1; sort the pages and list every role."""
        for role, numbers in value.items():
            if role not in PAGE_ROLES:
                raise ValueError("Unknown page role '" + str(role) + "'")
            if any(n < 1 for n in numbers):
                raise ValueError("Page numbers are 1-based, got " + str(numbers))
        return {role: sorted(set(value.get(role, []))) for role in PAGE_ROLES}


def normalize_key(text):
    """ Comparison key of an identifier or folder name.

    Args:
      - text (str) : Identifier or folder name.
    Returns: Lowercase string without spaces, dashes or underscores.
    """
    return str(text).replace("_", "").replace("-", "").replace(" ", "").lower()


def load_manifest(manifest_file=None):
    """ Read and validate the registry.

    Args:
      - manifest_file (Path | None) : Registry file, data/manifests/manuals.json by default.
    Returns: List of ManualEntry in file order.
    Raises: ValueError for an invalid entry or a repeated identifier.
    """
    path = Path(manifest_file) if manifest_file else MANIFEST_FILE
    with open(path, "r", encoding="utf-8") as f:
        manuals = [ManualEntry(**item) for item in json.load(f).get("manuals", [])]
    seen = set()
    for manual in manuals:
        key = normalize_key(manual.manual_id)
        if key in seen:
            raise ValueError("Manual identifier listed twice: " + manual.manual_id)
        seen.add(key)
    return manuals


def get_manual_entry(name, manifest_file=None):
    """ Registry entry of a manual, found by identifier or folder name.

    Args:
      - name (str) : Manual identifier or folder name.
      - manifest_file (Path | None) : Registry file.
    Returns: ManualEntry, or None when the manual is not registered.
    """
    key = normalize_key(name)
    for manual in load_manifest(manifest_file):
        if key in (normalize_key(manual.manual_id), normalize_key(manual.folder)):
            return manual
    return None


def manuals_in_split(split, manifest_file=None):
    """ Identifiers of the manuals of one split.

    Args:
      - split (str) : train, dev, test or unused.
      - manifest_file (Path | None) : Registry file.
    Returns: List of identifiers in registry order.
    """
    return [m.manual_id for m in load_manifest(manifest_file) if m.split == split]


def find_manual_dir(name, base_dir=None, manifest_file=None):
    """ Page folder of a registered manual.

    Args:
      - name (str) : Manual identifier or folder name.
      - base_dir (Path | None) : Parent of the page folders, data/extracted_manuals by default.
      - manifest_file (Path | None) : Registry file.
    Returns: Path of the folder.
    Raises: FileNotFoundError when the manual is not registered or its folder is missing.
    """
    manual = get_manual_entry(name, manifest_file)
    if manual is None:
        raise FileNotFoundError("Manual is not registered: " + str(name))
    folder = (Path(base_dir) if base_dir else EXTRACTED_MANUALS_DIR) / manual.folder
    if not folder.is_dir():
        raise FileNotFoundError("Page folder not found: " + str(folder))
    return folder


def page_image_name(manual_id, page_number):
    """ File name of a rendered page.

    Args:
      - manual_id (str) : Manual identifier.
      - page_number (int) : 1-based page number.
    Returns: Name such as 'Toshiba_SY_330_page_007.png'.
    """
    return manual_id + "_page_" + str(page_number).zfill(3) + ".png"
