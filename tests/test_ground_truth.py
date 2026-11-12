"""
Unit tests for the ground truth data contract.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.evaluation.ground_truth import ComponentGT, ManualGT, load_all_ground_truth, load_ground_truth

GT_DIR = Path(__file__).parent.parent / "data" / "ground_truth"


def make_component(**overrides):
    """ Build a valid component dictionary, then apply overrides."""
    base = {
        "refdes": "R102", "component_type": "Resistor",
        "page_bom": 7, "bbox_table": [10, 10, 60, 30],
        "page_schema": 2, "bbox_schema": [100, 100, 140, 120],
        "page_pcb": 6, "bbox_pcb": [300, 300, 340, 320],
    }
    base.update(overrides)
    return base


def test_real_files_load():
    """ Verify both committed ground truth files pass validation."""
    manuals = load_all_ground_truth(GT_DIR)
    assert set(manuals) == {"Toshiba_SY_330", "McIntosh_MC_2100"}
    assert manuals["Toshiba_SY_330"].total_components == 158
    assert manuals["McIntosh_MC_2100"].total_components == 162


def test_tri_sync_candidates_on_real_files():
    """ Verify the number of components annotated in all three views."""
    assert len(load_ground_truth(GT_DIR / "Toshiba_SY_330.json").tri_sync_candidates()) == 135
    assert len(load_ground_truth(GT_DIR / "McIntosh_MC_2100.json").tri_sync_candidates()) == 34


def test_refdes_is_normalized():
    """ Verify RefDes are stripped and uppercased."""
    assert ComponentGT(**make_component(refdes=" r102 ")).refdes == "R102"


@pytest.mark.parametrize("box", [[10, 10, 5, 30], [10, 30, 60, 10], [-1, 0, 5, 5], [1, 2, 3]])
def test_invalid_boxes_are_rejected(box):
    """ Verify inverted, negative and malformed boxes fail."""
    with pytest.raises(ValidationError):
        ComponentGT(**make_component(bbox_schema=box))


def test_box_without_page_is_rejected():
    """ Verify a box cannot be given without its page number."""
    with pytest.raises(ValidationError):
        ComponentGT(**make_component(page_pcb=None))


def test_unknown_type_and_rotation_are_rejected():
    """ Verify unknown component types and non-orthogonal rotations fail."""
    with pytest.raises(ValidationError):
        ComponentGT(**make_component(component_type="Valve"))
    with pytest.raises(ValidationError):
        ComponentGT(**make_component(rotation_schema=45.0))


def test_view_flags():
    """ Verify view flags and the tri-sync predicate."""
    full = ComponentGT(**make_component())
    assert full.has_bom and full.has_schematic and full.has_pcb and full.is_tri_sync_candidate
    no_pcb = ComponentGT(**make_component(page_pcb=None, bbox_pcb=None))
    assert no_pcb.has_pcb is False
    assert no_pcb.is_tri_sync_candidate is False


def test_manual_key_mismatch_is_rejected():
    """ Verify dictionary keys must match the component RefDes."""
    with pytest.raises(ValidationError):
        ManualGT(manual_id="M", device_model="M", components={"R1": make_component(refdes="R2")})


def test_total_components_is_recomputed():
    """ Verify a wrong stored count is replaced by the real one."""
    gt = ManualGT(manual_id="M", device_model="M", total_components=99, components={"R102": make_component()})
    assert gt.total_components == 1


def test_missing_file_raises():
    """ Verify a missing file gives a clear error."""
    with pytest.raises(FileNotFoundError):
        load_ground_truth(GT_DIR / "Does_Not_Exist.json")
