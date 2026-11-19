"""
Unit tests for the manual registry.
"""

import json

import pytest

from src.ingestion.manifest import (
    find_manual_dir,
    get_manual_entry,
    load_manifest,
    manuals_in_split,
    page_image_name,
)


def write_manifest(tmp_path, manuals):
    """ Write a registry file and return its path."""
    path = tmp_path / "manuals.json"
    path.write_text(json.dumps({"manuals": manuals}), encoding="utf-8")
    return path


ENTRY = {"manual_id": "Demo_100", "folder": "Demo-100 Service Manual", "device_model": "Demo 100", "split": "dev",
         "pages": {"bom": [8, 7], "schematic": [2], "pcb": [6]}}


def test_load_sorts_pages_and_fills_missing_roles(tmp_path):
    """ Page lists are sorted and a role without pages is an empty list."""
    entry = dict(ENTRY, pages={"bom": [8, 7]})
    manual = load_manifest(write_manifest(tmp_path, [entry]))[0]
    assert manual.pages == {"bom": [7, 8], "schematic": [], "pcb": []}


@pytest.mark.parametrize("change", [
    {"split": "validation"},
    {"pages": {"bom": [0]}},
    {"pages": {"cover": [1]}},
    {"manual_id": ""},
])
def test_invalid_entries_are_refused(tmp_path, change):
    """ Unknown split, page 0, unknown role or empty identifier stop the load."""
    with pytest.raises(ValueError):
        load_manifest(write_manifest(tmp_path, [dict(ENTRY, **change)]))


def test_duplicate_identifier_is_refused(tmp_path):
    """ Two entries with one identifier are refused."""
    with pytest.raises(ValueError):
        load_manifest(write_manifest(tmp_path, [ENTRY, dict(ENTRY, folder="other")]))


def test_lookup_by_identifier_or_folder(tmp_path):
    """ A manual is found by its identifier or its folder name, whatever the case and separators."""
    path = write_manifest(tmp_path, [ENTRY])
    assert get_manual_entry("demo_100", path).folder == "Demo-100 Service Manual"
    assert get_manual_entry("Demo-100 Service Manual", path).manual_id == "Demo_100"
    assert get_manual_entry("Unknown", path) is None


def test_manuals_in_split(tmp_path):
    """ Identifiers of one split, in registry order."""
    path = write_manifest(tmp_path, [ENTRY, dict(ENTRY, manual_id="B", folder="b", split="test")])
    assert manuals_in_split("test", path) == ["B"]


def test_find_manual_dir(tmp_path):
    """ The page folder of a registered manual is found; a missing one raises."""
    path = write_manifest(tmp_path, [ENTRY])
    (tmp_path / "pages" / "Demo-100 Service Manual").mkdir(parents=True)
    assert find_manual_dir("Demo_100", tmp_path / "pages", path).name == "Demo-100 Service Manual"
    with pytest.raises(FileNotFoundError):
        find_manual_dir("Unknown", tmp_path / "pages", path)


def test_page_image_name():
    """ Page images are named after the manual identifier and the zero-padded page number."""
    assert page_image_name("Demo_100", 7) == "Demo_100_page_007.png"


def test_registry_of_the_repository_loads():
    """ The committed registry is valid and has one dev manual."""
    manuals = load_manifest()
    assert len(manuals) >= 3 and len([m for m in manuals if m.split == "dev"]) == 1
