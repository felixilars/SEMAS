"""
Unit tests for the data model: boxes, parts list rows, occurrences and the manual graph.
"""

import pytest
from pydantic import ValidationError

from src.graph.entities import BBox, BOMItem, ManualGraph, Occurrence

def test_bbox_is_clamped_to_the_page():
    """ Coordinates slightly outside [0, 1] after a crop remap are clamped."""
    box = BBox(x1=-0.01, y1=0.2, x2=1.02, y2=0.8)
    assert (box.x1, box.x2) == (0.0, 1.0)

@pytest.mark.parametrize("coords", [(0.6, 0.2, 0.3, 0.8), (0.1, 0.9, 0.5, 0.3)])
def test_bbox_inverted_corners_are_refused(coords):
    """ x2 < x1 or y2 < y1 is a coordinate error."""
    with pytest.raises(ValidationError):
        BBox(x1=coords[0], y1=coords[1], x2=coords[2], y2=coords[3])

def test_bbox_pixels_round_trip():
    """ A pixel box survives normalization and back on a 1000 x 2000 page."""
    box = BBox.from_pixels([100, 400, 500, 1600], 1000, 2000)
    assert (box.x1, box.y2) == (0.1, 0.8)
    assert box.to_pixels(1000, 2000) == [100, 400, 500, 1600]

def test_bom_item_normalizes_refdes_and_text():
    """ RefDes is uppercased and text fields are stripped; empty specs become None."""
    item = BOMItem(ref_des=" r102 ", raw_description=" Carbon 47k ", page_number=6, value="", tolerance=" 5% ")
    assert (item.ref_des, item.raw_description, item.value, item.tolerance) == ("R102", "Carbon 47k", None, "5%")

def occurrence(ref_des, view, page=2, status="auto"):
    """ Occurrence with a fixed box."""
    return Occurrence(ref_des=ref_des, view=view, page_number=page, bbox=BBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2), status=status)

def test_graph_collects_occurrences_per_view():
    """ Occurrences of one RefDes go to one entity; tri-sync needs the three views."""
    graph = ManualGraph(manual_id="Demo", device_model="Demo")
    for view in ("bom", "schematic"):
        graph.add_occurrence(occurrence("R1", view))
    assert not graph.entities["R1"].is_tri_sync
    graph.add_occurrence(occurrence("r1", "pcb"))
    assert graph.entities["R1"].is_tri_sync and len(graph.entities) == 1

def test_review_and_unresolved_occurrences_stay_out_of_entities():
    """ Only auto-linked occurrences join an entity."""
    graph = ManualGraph(manual_id="Demo", device_model="Demo")
    graph.add_occurrence(occurrence("R1", "schematic", status="review"))
    graph.add_occurrence(occurrence("X?", "pcb", status="unresolved"))
    assert graph.entities == {} and len(graph.review_queue) == 1 and len(graph.unresolved) == 1

def test_unknown_view_is_refused():
    """ A view outside bom, schematic and pcb is an error."""
    with pytest.raises(ValidationError):
        occurrence("R1", "front_panel")

def test_graph_save_and_load(tmp_path):
    """ A saved graph loads back equal."""
    graph = ManualGraph(manual_id="Demo", device_model="Demo")
    graph.add_occurrence(occurrence("R1", "bom", page=7))
    graph.save_json(tmp_path / "graph.json")
    assert ManualGraph.load_json(tmp_path / "graph.json") == graph
