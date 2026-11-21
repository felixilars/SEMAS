"""
End-to-end Scoring
==================
Scores a recognition graph against the ground truth of the same manual, with no help from
the ground truth during recognition.

- Tri-sync candidate: component annotated in the parts list, the schematic and the PCB.
- A candidate is linked when the graph entity of its RefDes has a parts list occurrence on
  its parts list page, and an occurrence with IoU >= threshold on its schematic box and on
  its PCB box (same page).
- T_link = linked / candidates. Link precision = linked / entities of the graph found in the
  three views. The boxes of the graph are page-normalized, those of the ground truth are in
  pixels: they are compared after normalizing the ground truth box with the page size.

Usage:
  python -m src.evaluation.evaluate_graph --manual Toshiba_SY_330 --graph <graph.json> --out <result.json>
"""

import argparse
import json
import re
from pathlib import Path

from PIL import Image

from src.evaluation.ground_truth import load_ground_truth
from src.evaluation.metrics import compute_iou, precision_recall_f1
from src.graph.entities import VIEWS, BBox, ManualGraph
from src.ingestion.manifest import PROJECT_ROOT, find_manual_dir

GT_DIR = PROJECT_ROOT / "data" / "ground_truth"
PAGE_NUMBER = re.compile(r"_page_(\d+)\.png$")

def page_sizes(manual_dir):
    """ Pixel size of every rendered page of a manual folder.

    Args:
      - manual_dir (Path) : Folder with one subfolder per view.
    Returns: Dict {(view, page number): (width, height)}.
    """
    sizes = {}
    for view in VIEWS:
        for image in sorted((Path(manual_dir) / view).glob("*.png")):
            match = PAGE_NUMBER.search(image.name)
            if match:
                with Image.open(image) as page:
                    sizes[(view, int(match.group(1)))] = page.size
    return sizes

def found_at(entity, view, page, box, sizes, iou_thresh):
    """ Whether an entity has an occurrence on a ground truth label.

    Args:
      - entity (Entity | None) : Graph entity of the RefDes.
      - view (str) : schematic or pcb.
      - page (int) : Ground truth page.
      - box (list) : Ground truth box in pixels.
      - sizes (dict) : Output of page_sizes.
      - iou_thresh (float) : Minimum IoU.
    Returns: True when one occurrence of that view and page overlaps the label enough.
    """
    if entity is None or (view, page) not in sizes:
        return False
    target = BBox.from_pixels(box, *sizes[(view, page)])
    target = [target.x1, target.y1, target.x2, target.y2]
    return any(
        o.page_number == page and compute_iou([o.bbox.x1, o.bbox.y1, o.bbox.x2, o.bbox.y2], target) >= iou_thresh
        for o in entity.occurrences[view]
    )

def evaluate_graph(graph, gt, sizes, iou_thresh=0.5):
    """ Score a graph against the ground truth.

    Args:
      - graph (ManualGraph) : Recognition result.
      - gt (ManualGT) : Ground truth of the same manual.
      - sizes (dict) : Output of page_sizes for the manual.
      - iou_thresh (float) : Minimum IoU of a schematic or PCB match.
    Returns: Dict with counts, percentages, per-view hits and the linked RefDes.
    """
    hits = {view: 0 for view in VIEWS}
    linked = []
    candidates = gt.tri_sync_candidates()
    for comp in candidates:
        entity = graph.entities.get(comp.refdes)
        found = {
            "bom": entity is not None and any(o.page_number == comp.page_bom for o in entity.occurrences["bom"]),
            "schematic": found_at(entity, "schematic", comp.page_schema, comp.bbox_schema, sizes, iou_thresh),
            "pcb": found_at(entity, "pcb", comp.page_pcb, comp.bbox_pcb, sizes, iou_thresh),
        }
        for view in VIEWS:
            hits[view] += found[view]
        if all(found.values()):
            linked.append(comp.refdes)

    claimed = sum(1 for entity in graph.entities.values() if entity.is_tri_sync)
    precision, recall, f1 = precision_recall_f1(len(linked), claimed - len(linked), len(candidates) - len(linked))
    return {
        "manual_id": gt.manual_id,
        "iou_thresh": iou_thresh,
        "tri_sync_candidates": len(candidates),
        "linked": len(linked),
        "claimed": claimed,
        "t_link_pct": round(100 * recall, 2),
        "link_precision_pct": round(100 * precision, 2),
        "link_f1_pct": round(100 * f1, 2),
        "per_view_hits": hits,
        "review_queue": len(graph.review_queue),
        "linked_refdes": linked,
    }

def main():
    """ Score one graph file and write the result."""
    parser = argparse.ArgumentParser(description="Score a recognition graph against the ground truth")
    parser.add_argument("--manual", required=True, help="Manual identifier of the registry")
    parser.add_argument("--graph", required=True, help="Graph JSON written by the pipeline")
    parser.add_argument("--iou", type=float, default=0.5, help="Minimum IoU of a schematic or PCB match")
    parser.add_argument("--out", required=True, help="Result JSON")
    args = parser.parse_args()

    result = evaluate_graph(ManualGraph.load_json(args.graph), load_ground_truth(GT_DIR / (args.manual + ".json")),
                            page_sizes(find_manual_dir(args.manual)), args.iou)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("[RESULT] T_link " + str(result["linked"]) + "/" + str(result["tri_sync_candidates"]) + " = " + str(result["t_link_pct"]) + "%")
    print("[RESULT] Link precision " + str(result["link_precision_pct"]) + "% (" + str(result["claimed"]) + " entities in the three views)")
    print("[RESULT] Per-view hits " + str(result["per_view_hits"]))
    print("[INFO] Saved: " + str(out))

if __name__ == "__main__":
    main()
