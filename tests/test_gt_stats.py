"""
Unit tests for the ground truth statistics.
"""

from src.evaluation.ground_truth import ManualGT
from src.evaluation.gt_stats import manual_stats
from src.ingestion.manifest import ManualEntry

BOX = [10, 10, 20, 20]

def make_gt():
    """ Four components: one in all three views, one BOM and schematic, one schematic and PCB, one BOM only."""
    def comp(refdes, ctype, bom=None, sch=None, pcb=None):
        return {"refdes": refdes, "component_type": ctype, "page_bom": bom, "bbox_table": BOX if bom else None,
                "page_schema": sch, "bbox_schema": BOX if sch else None, "page_pcb": pcb, "bbox_pcb": BOX if pcb else None}
    components = [comp("R1", "Resistor", 7, 2, 6), comp("C1", "Capacitor", 7, 2), comp("Q1", "Transistor", None, 5, 6), comp("D1", "Diode", 8)]
    return ManualGT(manual_id="Demo", device_model="Demo", components={c["refdes"]: c for c in components})

def test_view_counts_and_candidates():
    """ Only a component present in the three views is a tri-sync candidate."""
    stats = manual_stats(make_gt())
    assert stats["components"] == 4
    assert stats["views"] == {"bom": 3, "schematic": 3, "pcb": 2}
    assert stats["tri_sync_candidates"] == 1
    assert stats["coverage"] == {"bom+schematic+pcb": 1, "bom+schematic": 1, "schematic+pcb": 1, "bom": 1}
    assert stats["candidates_by_type"] == {"Resistor": 1}

def test_pages_outside_the_registry_are_reported():
    """ A ground truth page missing from the hand-sorted page table is listed."""
    entry = ManualEntry(manual_id="Demo", folder="demo", device_model="Demo", split="dev", pages={"bom": [7], "schematic": [2, 5], "pcb": [6]})
    stats = manual_stats(make_gt(), entry)
    assert stats["split"] == "dev"
    assert stats["pages"]["bom"] == [7, 8]
    assert stats["pages_not_in_registry"] == {"bom": [8], "schematic": [], "pcb": []}

def test_unregistered_manual():
    """ Without a registry entry the split is unknown and no page check is made."""
    stats = manual_stats(make_gt())
    assert stats["split"] is None and stats["pages_not_in_registry"] is None
