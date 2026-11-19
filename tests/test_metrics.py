"""
Unit tests for the evaluation metrics: box overlap, counts to rates, box matching.
"""

import pytest
from src.evaluation.metrics import compute_iou, match_boxes, precision_recall_f1

def test_iou_identical_boxes():
    """ A box overlaps itself completely."""
    assert compute_iou([10, 10, 20, 20], [10, 10, 20, 20]) == 1.0

def test_iou_half_overlap():
    """ Two 10x10 boxes shifted by 5 pixels share 50 of 150 pixels."""
    assert compute_iou([0, 0, 10, 10], [5, 0, 15, 10]) == pytest.approx(50 / 150)

def test_iou_disjoint_and_touching_boxes():
    """ Boxes that do not overlap, or only share an edge, have IoU 0."""
    assert compute_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert compute_iou([0, 0, 10, 10], [10, 0, 20, 10]) == 0.0

def test_iou_of_empty_boxes_is_zero():
    """ Two degenerate boxes do not divide by zero."""
    assert compute_iou([5, 5, 5, 5], [5, 5, 5, 5]) == 0.0

def test_iou_rejects_inverted_box():
    """ A box with x2 < x1 is a coordinate error, not an empty box."""
    with pytest.raises(ValueError):
        compute_iou([10, 0, 0, 10], [0, 0, 10, 10])

def test_precision_recall_f1():
    """ 8 true positives, 2 false positives, 4 misses."""
    precision, recall, f1 = precision_recall_f1(8, 2, 4)
    assert (precision, recall) == (0.8, pytest.approx(8 / 12))
    assert f1 == pytest.approx(2 * 0.8 * (8 / 12) / (0.8 + 8 / 12))

def test_precision_recall_f1_with_nothing():
    """ No prediction and no truth gives zeros, not a division error."""
    assert precision_recall_f1(0, 0, 0) == (0.0, 0.0, 0.0)

def test_match_boxes_one_to_one():
    """ Each truth is matched at most once, best overlap first."""
    truths = [[0, 0, 10, 10], [100, 100, 110, 110]]
    predictions = [[1, 1, 10, 10], [0, 0, 10, 10], [300, 300, 310, 310]]
    pairs, lonely_predictions, lonely_truths = match_boxes(predictions, truths, 0.5)
    assert pairs == [(1, 0)]
    assert lonely_predictions == [0, 2] and lonely_truths == [1]

def test_match_boxes_threshold():
    """ An overlap under the threshold is not a match."""
    pairs, _, lonely_truths = match_boxes([[5, 0, 15, 10]], [[0, 0, 10, 10]], 0.5)
    assert pairs == [] and lonely_truths == [0]