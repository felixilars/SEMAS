"""
Unit tests for page rendering from the registry tables.
"""

import pymupdf

from src.ingestion.extract_pages import extract_pages_to_images, registry_tables
from src.ingestion.manifest import ManualEntry


def test_pages_are_rendered_under_their_role(tmp_path):
    """ Listed pages are rendered at 300 DPI into <folder>/<role>/, named after the manual identifier."""
    raw = tmp_path / "raw"
    raw.mkdir()
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page(width=72, height=144)
    doc.save(str(raw / "Demo-100 Service Manual.pdf"))
    doc.close()

    manual = ManualEntry(manual_id="Demo_100", folder="Demo-100 Service Manual", device_model="Demo", split="dev",
                         pages={"bom": [3], "schematic": [1], "pcb": [9]})
    pages_table, manual_ids = registry_tables([manual])
    extract_pages_to_images(pages_table, raw, tmp_path / "out", manual_ids)

    folder = tmp_path / "out" / "Demo-100 Service Manual"
    image = pymupdf.Pixmap(str(folder / "bom" / "Demo_100_page_003.png"))
    assert (image.width, image.height) == (300, 600)
    assert (folder / "schematic" / "Demo_100_page_001.png").exists()
    assert not (folder / "pcb").exists() or not any((folder / "pcb").iterdir())
