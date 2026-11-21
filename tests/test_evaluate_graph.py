"""
Unit tests for the end-to-end scoring of a graph against the ground truth.
"""

from src.evaluation.evaluate_graph import evaluate_graph
from src.evaluation.ground_truth import ManualGT
from src.graph.entities import BBox, ManualGraph, Occurrence

SIZES = {("bom", 7): (1000, 2000), ("schematic", 2): (1000, 2000), ("pcb", 6): (2000, 1000)}

def make_gt():
    """ R1 and C1 annotated in the three views; D1 in the parts list only."""
    def comp(refdes, ctype, sch_box, pcb_box):
        return {"refdes": refdes, "component_type": ctype, "page_bom": 7, "bbox_table": [10, 10, 60, 30],
                "page_schema": 2, "bbox_schema": sch_box, "page_pcb": 6, "bbox_pcb": pcb_box}
    components = [comp("R1", "Resistor", [100, 200, 200, 300], [400, 100, 600, 200]),
                  comp("C1", "Capacitor", [500, 500, 600, 600], [800, 800, 900, 900]),
                  {"refdes": "D1", "component_type": "Diode", "page_bom": 7, "bbox_table": [10, 40, 60, 60]}]
    return ManualGT(manual_id="Demo", device_model="Demo", components={c["refdes"]: c for c in components})

def graph_from_gt(gt):
    """ Graph holding exactly the annotated boxes of the ground truth."""
    graph = ManualGraph(manual_id="Demo", device_model="Demo")
    for comp in gt.components.values():
        for view, page, box in (("bom", comp.page_bom, comp.bbox_table), ("schematic", comp.page_schema, comp.bbox_schema), ("pcb", comp.page_pcb, comp.bbox_pcb)):
            if page is not None and box is not None:
                width, height = SIZES[(view, page)]
                graph.add_occurrence(Occurrence(ref_des=comp.refdes, view=view, page_number=page, bbox=BBox.from_pixels(box, width, height)))
    return graph

def test_graph_built_from_the_ground_truth_scores_100():
    """ The ground truth scored against itself links every candidate with no wrong claim."""
    gt = make_gt()
    result = evaluate_graph(graph_from_gt(gt), gt, SIZES)
    assert (result["tri_sync_candidates"], result["linked"], result["claimed"]) == (2, 2, 2)
    assert (result["t_link_pct"], result["link_precision_pct"], result["link_f1_pct"]) == (100.0, 100.0, 100.0)
    assert result["per_view_hits"] == {"bom": 2, "schematic": 2, "pcb": 2}

def test_box_moved_off_the_label_is_a_miss():
    """ A schematic box that no longer overlaps its label breaks the link and counts as a wrong claim."""
    gt = make_gt()
    graph = graph_from_gt(gt)
    graph.entities["C1"].occurrences["schematic"][0].bbox = BBox.from_pixels([700, 1500, 800, 1600], 1000, 2000)
    result = evaluate_graph(graph, gt, SIZES)
    assert result["linked"] == 1 and result["per_view_hits"]["schematic"] == 1
    assert result["link_precision_pct"] == 50.0 and result["linked_refdes"] == ["R1"]

def test_right_box_on_the_wrong_page_is_a_miss():
    """ The same coordinates on another page are another place."""
    gt = make_gt()
    graph = graph_from_gt(gt)
    graph.entities["R1"].occurrences["pcb"][0].page_number = 9
    assert evaluate_graph(graph, gt, SIZES)["per_view_hits"]["pcb"] == 1

def test_entity_absent_from_the_candidates_lowers_precision():
    """ A tri-sync entity the ground truth does not list as a candidate is a wrong claim."""
    gt = make_gt()
    graph = graph_from_gt(gt)
    box = BBox(x1=0.0, y1=0.0, x2=0.1, y2=0.1)
    for view, page in (("schematic", 2), ("pcb", 6)):
        graph.add_occurrence(Occurrence(ref_des="D1", view=view, page_number=page, bbox=box))
    result = evaluate_graph(graph, gt, SIZES)
    assert (result["linked"], result["claimed"]) == (2, 3) and result["link_precision_pct"] == 66.67

def test_empty_graph():
    """ An empty graph scores zero without dividing by zero."""
    result = evaluate_graph(ManualGraph(manual_id="Demo", device_model="Demo"), make_gt(), SIZES)
    assert (result["t_link_pct"], result["link_precision_pct"], result["link_f1_pct"]) == (0.0, 0.0, 0.0)
