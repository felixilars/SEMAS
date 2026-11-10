"""
Unit Tests for Levenshtein Numeric Mutation Diagnostics
======================================================
Validates raw edit distance computation, numeric mutation detection, and collision risk flags.
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from notebooks.debug_levenshtein_trap import (
    compute_raw_levenshtein,
    find_raw_nearest_match,
    extract_numeric_sequence,
    check_numeric_mutation,
    evaluate_mutation_risks,
)

def test_compute_raw_levenshtein_unit_costs():
    """ Verify basic insertion, deletion, and substitution calculations."""
    assert compute_raw_levenshtein("R101", "R101") == 0
    assert compute_raw_levenshtein("R10", "R101") == 1
    assert compute_raw_levenshtein("R101", "R102") == 1
    assert compute_raw_levenshtein("R101", "C101") == 1

def test_raw_levenshtein_mutates_numeric_indices():
    """ Verify vulnerability where raw Levenshtein finds distance 1 between distinct components."""
    lexicon = {"R102", "R103"}
    matched, dist = find_raw_nearest_match("R10", lexicon)

    # Raw Levenshtein matches R10 to R102 with distance 1
    assert dist == 1
    assert matched == "R102"
    # Demonstrates that R10 was mutated into R102
    assert check_numeric_mutation("R10", matched) is True

def test_check_numeric_mutation_flags_collisions():
    """ Verify numeric mutation check correctly flags differing numbers."""
    assert check_numeric_mutation("R101", "R102") is True
    assert check_numeric_mutation("R10", "R102") is True
    assert check_numeric_mutation("C201", "C205") is True
    assert check_numeric_mutation("Q101", "Q102") is True

def test_check_numeric_mutation_allows_identical_numbers():
    """ Verify numeric mutation check passes identical numeric sequences."""
    assert check_numeric_mutation("R101", "R101") is False
    assert check_numeric_mutation("R101A", "R101") is False
    assert check_numeric_mutation("R101", "C101") is False  # Same number, different prefix

def test_extract_numeric_sequence():
    """ Verify extraction of contiguous digit sequences."""
    assert extract_numeric_sequence("R101") == "101"
    assert extract_numeric_sequence("C05") == "05"
    assert extract_numeric_sequence("Q102B") == "102"
    assert extract_numeric_sequence("RESISTOR") == ""
    assert extract_numeric_sequence("") == ""

def test_evaluate_mutation_risks_simulation():
    """ Verify full simulation flags collision risk rate."""
    lexicon = {"R102", "R103"}
    test_cases = [
        {"query": "R10", "expected": "R101", "failure_mode": "Truncated"},
    ]
    results = evaluate_mutation_risks(test_cases, lexicon)

    assert len(results) == 1
    assert results[0]["collision"] is True
    assert results[0]["numeric_mutated"] is True


def test_nearest_match_is_independent_of_iteration_order():
    """ Verify tie-breaking is deterministic whatever the lexicon order or hash seed."""
    import os
    import subprocess
    import sys

    assert find_raw_nearest_match("R10", ["R103", "R102"]) == ("R102", 1)
    assert find_raw_nearest_match("R10", ["R102", "R103"]) == ("R102", 1)
    assert find_raw_nearest_match("R10", []) == (None, 999)

    root = Path(__file__).parent.parent
    code = (
        "from notebooks.debug_levenshtein_trap import find_raw_nearest_match\n"
        "print(find_raw_nearest_match('R10', {'R101', 'R102', 'R103', 'R104'}))\n"
    )
    outputs = set()
    for seed in ["0", "1", "2", "3", "4"]:
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = seed
        proc = subprocess.run([sys.executable, "-c", code], cwd=str(root), env=env, capture_output=True, text=True, check=True)
        outputs.add(proc.stdout.strip())
    assert len(outputs) == 1


def test_tied_candidates_flag_ambiguous_matches():
    """ Verify a truncated index tied with several components is reported as ambiguous."""
    lexicon = {"R101", "R102", "R103"}
    results = evaluate_mutation_risks([{"query": "R10", "expected": "R101", "failure_mode": "Truncated"}], lexicon)
    assert results[0]["collision"] is False  # alphabetical tie-break happens to pick R101
    assert results[0]["tied_candidates"] == 3
    assert results[0]["ambiguous"] is True

    exact = evaluate_mutation_risks([{"query": "R102", "expected": "R102", "failure_mode": "Exact"}], lexicon)
    assert exact[0]["tied_candidates"] == 1
    assert exact[0]["ambiguous"] is False
