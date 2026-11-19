"""
Evaluation Metrics
==================
Box overlap, detection rates and one-to-one matching of predicted boxes with ground truth
boxes. Boxes are [x1, y1, x2, y2] with x1 <= x2 and y1 <= y2, in the same coordinate
system on both sides (pixels of the 300 DPI page for the ground truth).
"""


def box_area(box):
    """ Area of a box.

    Args:
      - box (list) : [x1, y1, x2, y2].
    Returns: Area as a float, 0.0 for a degenerate box.
    Raises: ValueError when the corners are inverted.
    """
    x1, y1, x2, y2 = [float(v) for v in box]
    if x2 < x1 or y2 < y1:
        raise ValueError("Box corners are inverted: " + str(list(box)))
    return (x2 - x1) * (y2 - y1)


def compute_iou(box_a, box_b):
    """ Intersection over union of two boxes.

    Args:
      - box_a (list) : [x1, y1, x2, y2].
      - box_b (list) : [x1, y1, x2, y2].
    Returns: IoU in [0.0, 1.0]; 0.0 when the union is empty.
    Raises: ValueError when a box has inverted corners.
    """
    union_base = box_area(box_a) + box_area(box_b)
    width = min(float(box_a[2]), float(box_b[2])) - max(float(box_a[0]), float(box_b[0]))
    height = min(float(box_a[3]), float(box_b[3])) - max(float(box_a[1]), float(box_b[1]))
    intersection = max(0.0, width) * max(0.0, height)
    union = union_base - intersection
    return intersection / union if union > 0.0 else 0.0


def precision_recall_f1(true_positives, false_positives, false_negatives):
    """ Rates from match counts.

    Args:
      - true_positives (int) : Predictions matched with a truth.
      - false_positives (int) : Predictions matched with nothing.
      - false_negatives (int) : Truths matched with nothing.
    Returns: Tuple (precision, recall, f1), each 0.0 when its denominator is 0.
    """
    precision = true_positives / max(1, true_positives + false_positives)
    recall = true_positives / max(1, true_positives + false_negatives)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
    return precision, recall, f1


def match_boxes(predictions, truths, iou_thresh):
    """ Match predicted boxes with truth boxes, one to one, largest overlap first.

    Args:
      - predictions (list) : Predicted boxes.
      - truths (list) : Ground truth boxes.
      - iou_thresh (float) : Minimum IoU of a match.
    Returns: Tuple (pairs, unmatched_predictions, unmatched_truths): pairs is a list of
      (prediction index, truth index); the two others are sorted index lists.
    """
    candidates = []
    for p_index, p_box in enumerate(predictions):
        for t_index, t_box in enumerate(truths):
            iou = compute_iou(p_box, t_box)
            if iou >= iou_thresh:
                candidates.append((-iou, p_index, t_index))
    candidates.sort()

    pairs = []
    used_predictions = set()
    used_truths = set()
    for _, p_index, t_index in candidates:
        if p_index in used_predictions or t_index in used_truths:
            continue
        pairs.append((p_index, t_index))
        used_predictions.add(p_index)
        used_truths.add(t_index)

    unmatched_predictions = [i for i in range(len(predictions)) if i not in used_predictions]
    unmatched_truths = [i for i in range(len(truths)) if i not in used_truths]
    return pairs, unmatched_predictions, unmatched_truths
