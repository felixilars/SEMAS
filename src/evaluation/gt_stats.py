"""
Ground Truth Statistics
=======================
Counts per manual: components, components annotated in each view, tri-sync candidates
(annotated in the parts list, the schematic and the PCB) and pages used. A tri-sync
candidate is the denominator of T_link, so only components present in the three views count.

Usage:
  python -m src.evaluation.gt_stats --out results/week1/gt_stats.json
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from src.evaluation.ground_truth import load_all_ground_truth
from src.ingestion.manifest import PAGE_ROLES, PROJECT_ROOT, get_manual_entry

GT_DIR = PROJECT_ROOT / "data" / "ground_truth"
VIEW_TESTS = {"bom": "has_bom", "schematic": "has_schematic", "pcb": "has_pcb"}
VIEW_PAGES = {"bom": "page_bom", "schematic": "page_schema", "pcb": "page_pcb"}

def manual_stats(gt, entry=None):
    """ Statistics of one ground truth file.

    Args:
      - gt (ManualGT) : Ground truth of a manual.
      - entry (ManualEntry | None) : Registry entry of the manual, for its split and page table.
    Returns: Dict with component, view, coverage and page counts.
    """
    components = list(gt.components.values())
    coverage = Counter("+".join(v for v in PAGE_ROLES if getattr(c, VIEW_TESTS[v])) for c in components)
    candidates = gt.tri_sync_candidates()
    pages = {v: sorted(set(getattr(c, VIEW_PAGES[v]) for c in components if getattr(c, VIEW_TESTS[v]))) for v in PAGE_ROLES}
    return {
        "manual_id": gt.manual_id,
        "split": entry.split if entry else None,
        "components": len(components),
        "views": {v: sum(1 for c in components if getattr(c, VIEW_TESTS[v])) for v in PAGE_ROLES},
        "tri_sync_candidates": len(candidates),
        "coverage": dict(coverage.most_common()),
        "candidates_by_type": dict(Counter(c.component_type for c in candidates).most_common()),
        "pages": pages,
        "pages_not_in_registry": {v: [p for p in pages[v] if p not in entry.pages[v]] for v in PAGE_ROLES} if entry else None,
    }

def main():
    """ Print the statistics of every ground truth file and write them to JSON."""
    parser = argparse.ArgumentParser(description="Ground truth statistics per manual")
    parser.add_argument("--gt-dir", default=str(GT_DIR), help="Folder of the ground truth files")
    parser.add_argument("--out", required=True, help="Result JSON")
    args = parser.parse_args()

    rows = [manual_stats(gt, get_manual_entry(manual_id)) for manual_id, gt in load_all_ground_truth(args.gt_dir).items()]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"manuals": rows}, f, indent=2)
    for row in rows:
        print("[RESULT] " + row["manual_id"] + " (" + str(row["split"]) + "): " + str(row["components"]) + " components, "
              + str(row["tri_sync_candidates"]) + " tri-sync candidates, views " + str(row["views"]))
        if row["pages_not_in_registry"] and any(row["pages_not_in_registry"].values()):
            print("[WARN] " + row["manual_id"] + ": ground truth pages missing from the registry " + str(row["pages_not_in_registry"]))
    print("[INFO] Saved: " + str(out))

if __name__ == "__main__":
    main()
