"""
Levenshtein Numeric Mutation Diagnostic Script
==============================================
Reproduces and evaluates component collision vulnerabilities when using unconstrained edit distance on electronic reference designators without numeric locks.
"""

from pathlib import Path
import re
import sys

sys.path.append(str(Path(__file__).parent.parent))

def compute_raw_levenshtein(s1, s2):
    """ Compute standard unconstrained Wagner-Fischer edit distance with unit costs.

    Args:
      - s1 (str) : First string.
      - s2 (str) : Second string.
    Returns: Integer edit distance.
    """
    if s1 == s2:
        return 0

    len1 = len(s1)
    len2 = len(s2)

    dp = [[0 for _ in range(len2 + 1)] for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j

    for i in range(1, len1 + 1):
        c1 = s1[i - 1]
        for j in range(1, len2 + 1):
            c2 = s2[j - 1]
            cost = 0 if c1 == c2 else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # Deletion
                dp[i][j - 1] + 1,       # Insertion
                dp[i - 1][j - 1] + cost  # Substitution
            )

    return dp[len1][len2]

def find_raw_nearest_match(query, lexicon):
    """ Find nearest candidate in lexicon using unconstrained edit distance.

    Ties are broken alphabetically so the result does not depend on the iteration
    order of a set (which changes with PYTHONHASHSEED).

    Args:
      - query (str) : OCR candidate string.
      - lexicon (iterable) : Target reference designators.
    Returns: Tuple of (best_candidate, distance), or (None, 999) for an empty lexicon.
    """
    best_cand = None
    best_dist = 999

    for target in sorted(lexicon):
        dist = compute_raw_levenshtein(query, target)
        if dist < best_dist:
            best_dist = dist
            best_cand = target

    return best_cand, best_dist

def count_tied_candidates(query, lexicon, best_dist):
    """ Count lexicon entries sharing the best edit distance to the query.

    More than one tied candidate means the match is ambiguous: whichever entry is
    picked, the choice is arbitrary and unsafe for an electronic component.

    Args:
      - query (str) : OCR candidate string.
      - lexicon (iterable) : Target reference designators.
      - best_dist (int) : Best distance found for the query.
    Returns: Integer number of candidates at best_dist.
    """
    return sum(1 for target in lexicon if compute_raw_levenshtein(query, target) == best_dist)

def extract_numeric_sequence(token):
    """ Extract digit sequence from a component reference token.

    Args:
      - token (str) : Candidate token string.
    Returns: String of contiguous digits or empty string.
    """
    if not token:
        return ""
    match = re.search(r"\d+", str(token))
    return match.group(0) if match else ""

def check_numeric_mutation(s1, s2):
    """ Check whether mapping s1 to s2 mutates numeric component identity.

    Args:
      - s1 (str) : Source OCR token.
      - s2 (str) : Target candidate token.
    Returns: True if both tokens contain differing numeric parts, False otherwise.
    """
    num1 = extract_numeric_sequence(s1)
    num2 = extract_numeric_sequence(s2)
    if num1 and num2 and num1 != num2:
        return True
    return False

def evaluate_mutation_risks(test_cases, lexicon):
    """ Evaluate unconstrained Levenshtein behavior across vulnerable electronic test cases.

    Args:
      - test_cases (list) : List of dicts specifying query, ground truth, and failure mode.
      - lexicon (set) : Reference component lexicon.
    Returns: List of evaluation result dictionaries.
    """
    results = []
    for tc in test_cases:
        query = tc["query"]
        expected = tc["expected"]
        mode = tc["failure_mode"]

        matched, dist = find_raw_nearest_match(query, lexicon)
        is_mutated = check_numeric_mutation(query, matched)
        is_collision = (matched != expected)
        tied = count_tied_candidates(query, lexicon, dist)

        results.append({
            "query": query,
            "expected": expected,
            "matched": matched,
            "distance": dist,
            "numeric_mutated": is_mutated,
            "collision": is_collision,
            "tied_candidates": tied,
            "ambiguous": tied > 1,
            "failure_mode": mode,
        })

    return results

def format_diagnostic_report(results):
    """ Render an ASCII diagnostic table highlighting numeric mutation vulnerabilities.

    Args:
      - results (list) : List of evaluation result dictionaries.
    Returns: Formatted multi-line string.
    """
    lines = []
    divider = "=" * 90
    sub_divider = "-" * 90

    lines.append(divider)
    header = (
        "QUERY".ljust(12)
        + "EXPECTED".ljust(12)
        + "RAW MATCH".ljust(12)
        + "DIST".rjust(6)
        + "NUM MUTATED".rjust(14)
        + "COLLISION".rjust(12)
        + "TIES".rjust(6)
        + "   FAILURE MODE"
    )
    lines.append(header)
    lines.append(sub_divider)

    total = len(results)
    collisions = 0
    mutations = 0
    ambiguous = 0

    for r in results:
        if r["collision"]:
            collisions += 1
        if r["numeric_mutated"]:
            mutations += 1
        if r["ambiguous"]:
            ambiguous += 1

        mut_str = "[MUTATED]" if r["numeric_mutated"] else "PRESERVED"
        col_str = "[CRITICAL]" if r["collision"] else "OK"

        row = (
            r["query"].ljust(12)
            + r["expected"].ljust(12)
            + r["matched"].ljust(12)
            + str(r["distance"]).rjust(6)
            + mut_str.rjust(14)
            + col_str.rjust(12)
            + str(r["tied_candidates"]).rjust(6)
            + "   " + r["failure_mode"]
        )
        lines.append(row)

    lines.append(sub_divider)

    collision_rate = round((float(collisions) / float(max(1, total))) * 100.0, 1)
    summary_line = (
        "TOTAL CASES: " + str(total)
        + " | NUMERIC MUTATIONS: " + str(mutations)
        + " | CRITICAL COLLISIONS: " + str(collisions)
        + " (" + str(collision_rate) + "%)"
        + " | AMBIGUOUS (TIED) MATCHES: " + str(ambiguous)
    )
    lines.append(summary_line)
    lines.append("A tied match is unsafe even when the alphabetical tie-break happens to pick the expected component.")
    lines.append(divider)

    return "\n".join(lines)

def main():
    """ Run numeric mutation diagnostic simulation across sample circuit patterns."""
    print("[INFO] RUNNING UNCONSTRAINED LEVENSHTEIN COLLISION DIAGNOSTIC")

    # Sample lexicon representing adjacent active components in an audio amplifier stage
    sample_lexicon = {
        "R101", "R102", "R103", "R104", "R105",
        "C101", "C102", "C103",
        "Q101", "Q102",
        "S501",
    }

    test_cases = [
        {
            "query": "R10",
            "expected": "R101",
            "failure_mode": "Truncated tail digit auto-aliases to adjacent component R102",
        },
        {
            "query": "R107",
            "expected": "R101",
            "failure_mode": "Faint digit misread mutates into unrelated resistor R102",
        },
        {
            "query": "R104A",
            "expected": "R104",
            "failure_mode": "Sub-unit channel letter insertion",
        },
        {
            "query": "C10",
            "expected": "C101",
            "failure_mode": "Truncated capacitor index aliases to C102/C103",
        },
        {
            "query": "Q10",
            "expected": "Q101",
            "failure_mode": "Truncated transistor index aliases to Q102",
        },
    ]

    results = evaluate_mutation_risks(test_cases, sample_lexicon)
    report = format_diagnostic_report(results)
    print("\n" + report + "\n")
    print("[WARN] Unconstrained edit distance mutates distinct numeric indices.")
    print("[RESULT] Engineering directive: numeric identity lock must be enforced in post-correction.")

if __name__ == "__main__":
    main()
