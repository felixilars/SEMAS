"""
OCR Post-Correction and Lexicon Cross-Matching Engine
======================================================
Resolves raw OCR noisy tokens against dynamic manual lexicons (D_BOM)
using weighted Levenshtein distance with optical confusion penalties
and a 3-tier Human-in-the-Loop (HITL) triage system.
"""

from __future__ import annotations

import re


OPTICAL_CONFUSION_COSTS = {
    # Extreme optical confusion pairs (cost = 0.15)
    frozenset(["O", "0"]): 0.15,
    frozenset(["I", "1"]): 0.15,
    frozenset(["l", "1"]): 0.15,
    frozenset(["I", "l"]): 0.15,
    frozenset(["S", "5"]): 0.15,
    frozenset(["s", "5"]): 0.15,
    frozenset(["Z", "2"]): 0.15,
    frozenset(["z", "2"]): 0.15,
    frozenset(["B", "8"]): 0.15,
    frozenset(["G", "6"]): 0.15,

    # Moderate optical confusion pairs (cost = 0.35)
    frozenset(["D", "0"]): 0.35,
    frozenset(["C", "G"]): 0.35,
    frozenset(["U", "V"]): 0.35,
    frozenset(["V", "Y"]): 0.35,
    frozenset(["E", "F"]): 0.35,
    frozenset(["P", "R"]): 0.35,
    frozenset(["B", "3"]): 0.35,
    frozenset(["A", "4"]): 0.35,
}

# Recognized multi-letter component prefixes
MULTI_LETTER_PREFIXES = ("IC", "VR", "RV", "TR", "ZD", "SW", "PL", "CN", "TP", "CR", "FS", "TH")


def split_refdes_and_spec(raw_text):
    """ Separate attached electrical spec or value from reference designator.

    Args:
      - raw_text (str) : Raw text string produced by OCR (e.g. 'R184 33k' or 'R 101').
    Returns: Tuple of (clean_refdes, spec_value).
    """
    if not raw_text:
        return "", None

    cleaned = raw_text.strip()
    tokens = cleaned.split()
    if not tokens:
        return "", None

    if len(tokens) == 1:
        # Standalone token, no separated spec
        return tokens[0].upper(), None

    # Multi-token analysis
    tok0 = tokens[0].upper()
    tok1 = tokens[1]

    # Subcase: Space between prefix and number (e.g. ['R', '101'] or ['IC', '402'])
    if tok0.isalpha() and len(tok0) <= 3 and any(char.isdigit() for char in tok1):
        merged_refdes = tok0 + tok1.upper()
        remaining_spec = " ".join(tokens[2:]).strip() if len(tokens) > 2 else None
        return merged_refdes, remaining_spec

    # Standard case: First token is RefDes, following tokens are spec (e.g. ['R184', '33k'])
    refdes = tok0
    spec_value = " ".join(tokens[1:]).strip()
    return refdes, (spec_value if spec_value else None)


def extract_prefix(refdes_token):
    """ Extract canonical component family prefix from reference designator.

    Args:
      - refdes_token (str) : Reference designator string (e.g. 'R101', 'IC402', 'RO1').
    Returns: Canonical component family prefix string in uppercase.
    """
    if not refdes_token:
        return ""

    upper = refdes_token.upper()
    for multi in MULTI_LETTER_PREFIXES:
        if upper.startswith(multi):
            return multi

    # Return primary leading alphabetic family letter
    for char in upper:
        if char.isalpha():
            return char
    return ""


def compute_weighted_levenshtein(s1, s2):
    """ Compute weighted edit distance with optical confusion penalties.

    Args:
      - s1 (str) : First string (OCR candidate).
      - s2 (str) : Second string (lexicon target).
    Returns: Float weighted edit distance.
    """
    if s1 == s2:
        return 0.0

    len1 = len(s1)
    len2 = len(s2)

    # Matrix initialization
    dp = [[0.0 for _ in range(len2 + 1)] for _ in range(len1 + 1)]

    for i in range(len1 + 1):
        dp[i][0] = float(i)
    for j in range(len2 + 1):
        dp[0][j] = float(j)

    for i in range(1, len1 + 1):
        c1 = s1[i - 1]
        for j in range(1, len2 + 1):
            c2 = s2[j - 1]

            if c1 == c2:
                sub_cost = 0.0
            else:
                pair = frozenset([c1, c2])
                sub_cost = OPTICAL_CONFUSION_COSTS.get(pair, 1.0)

            del_cost = dp[i - 1][j] + 1.0
            ins_cost = dp[i][j - 1] + 1.0
            match_cost = dp[i - 1][j - 1] + sub_cost

            dp[i][j] = min(del_cost, ins_cost, match_cost)

    base_dist = dp[len1][len2]

    # Prefix mismatch penalty
    prefix1 = extract_prefix(s1)
    prefix2 = extract_prefix(s2)
    if prefix1 and prefix2 and prefix1 != prefix2:
        base_dist = base_dist + 2.5

    return base_dist


class CorrectionResult:
    """ Container for reference designator post-correction outcome."""

    def __init__(self, raw_text, extracted_refdes, spec_value, resolved_refdes, status, distance, confidence, candidates):
        """ Initialize correction result container.

        Args:
          - raw_text (str) : Original raw text from OCR.
          - extracted_refdes (str) : Normalized candidate reference designator.
          - spec_value (str | None) : Attached electrical spec value.
          - resolved_refdes (str) : Best matched target from dynamic lexicon.
          - status (str) : HITL status ('AUTO_LINKED', 'REVIEW_QUEUE', 'UNRESOLVED').
          - distance (float) : Weighted Levenshtein distance to resolved target.
          - confidence (float) : Confidence score between 0.0 and 1.0.
          - candidates (list) : List of candidate tuples (refdes, distance).
        Returns: None.
        """
        self.raw_text = raw_text
        self.extracted_refdes = extracted_refdes
        self.spec_value = spec_value
        self.resolved_refdes = resolved_refdes
        self.status = status
        self.distance = distance
        self.confidence = confidence
        self.candidates = candidates

    def to_dict(self):
        """ Convert result to standard dictionary.

        Args: None.
        Returns: Dictionary representation of correction result.
        """
        return {
            "raw_text": self.raw_text,
            "extracted_refdes": self.extracted_refdes,
            "spec_value": self.spec_value,
            "resolved_refdes": self.resolved_refdes,
            "status": self.status,
            "distance": round(self.distance, 3),
            "confidence": round(self.confidence, 3),
            "candidates": [(cand[0], round(cand[1], 3)) for cand in self.candidates],
        }


class PostCorrector:
    """ Resolves OCR text against dynamic manual lexicons with 3-tier HITL triage."""

    def __init__(self, lexicon=None, auto_threshold=0.5, review_threshold=1.6, margin_threshold=0.4):
        """ Initialize post-corrector instance.

        Args:
          - lexicon (set | list | None) : Set of valid component reference designators.
          - auto_threshold (float) : Maximum distance for automatic linking.
          - review_threshold (float) : Maximum distance for human review queue.
          - margin_threshold (float) : Minimum margin between top 2 candidates for auto-link.
        Returns: None.
        """
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold
        self.margin_threshold = margin_threshold

        self.lexicon = set()
        self.prefix_index = {}
        if lexicon:
            self.set_lexicon(lexicon)

    def set_lexicon(self, lexicon_items):
        """ Update dynamic lexicon index.

        Args:
          - lexicon_items (iterable) : Collection of valid reference designator strings.
        Returns: None.
        """
        self.lexicon = set()
        self.prefix_index = {}

        for item in lexicon_items:
            clean = str(item).strip().upper()
            if not clean:
                continue
            self.lexicon.add(clean)
            p = extract_prefix(clean)
            if p not in self.prefix_index:
                self.prefix_index[p] = []
            self.prefix_index[p].append(clean)

    def resolve(self, raw_text):
        """ Resolve noisy OCR text against the dynamic lexicon.

        Args:
          - raw_text (str) : Input text from OCR engine.
        Returns: CorrectionResult instance with resolved reference designator.
        """
        clean_ref, spec_val = split_refdes_and_spec(raw_text)

        if not clean_ref:
            return CorrectionResult(
                raw_text, "", spec_val, "", "UNRESOLVED", 99.0, 0.0, []
            )

        # 1. Exact match fast path
        if clean_ref in self.lexicon:
            return CorrectionResult(
                raw_text, clean_ref, spec_val, clean_ref, "AUTO_LINKED", 0.0, 1.0, [(clean_ref, 0.0)]
            )

        if not self.lexicon:
            # Lexicon is empty; keep cleaned text as unverified
            return CorrectionResult(
                raw_text, clean_ref, spec_val, clean_ref, "UNRESOLVED", 0.0, 0.5, []
            )

        # 2. Candidate generation
        cand_pool = []
        p = extract_prefix(clean_ref)

        # Prioritize matching prefix partition first
        if p in self.prefix_index:
            cand_pool.extend(self.prefix_index[p])

        # If prefix partition is empty or small, expand to entire lexicon
        if len(cand_pool) < 5:
            for item in self.lexicon:
                if item not in cand_pool:
                    cand_pool.append(item)

        # 3. Compute weighted Levenshtein distances
        scored = []
        for target in cand_pool:
            dist = compute_weighted_levenshtein(clean_ref, target)
            scored.append((target, dist))

        scored.sort(key=lambda x: x[1])
        top_candidates = scored[:5]

        best_target, best_dist = top_candidates[0]
        second_dist = top_candidates[1][1] if len(top_candidates) > 1 else 99.0

        # Compute confidence: inverse normalized distance
        conf = max(0.0, min(1.0, 1.0 - (best_dist / max(1.0, float(len(clean_ref))))))

        # 4. 3-Tier HITL Triage
        margin = second_dist - best_dist
        if best_dist <= self.auto_threshold and margin >= self.margin_threshold:
            status = "AUTO_LINKED"
        elif best_dist <= self.review_threshold:
            status = "REVIEW_QUEUE"
        else:
            status = "UNRESOLVED"

        return CorrectionResult(
            raw_text, clean_ref, spec_val, best_target, status, best_dist, conf, top_candidates
        )

    def process_predictions(self, pred_boxes):
        """ Post-correct a list of predicted component boxes in place.

        Args:
          - pred_boxes (list) : List of prediction dictionaries with 'text' field.
        Returns: List of enriched prediction dictionaries with correction results.
        """
        results = []
        for pred in pred_boxes:
            raw_text = pred.get("text", "")
            corr = self.resolve(raw_text)

            enriched = dict(pred)
            enriched["raw_ocr_text"] = raw_text
            enriched["text"] = corr.resolved_refdes if corr.status in ["AUTO_LINKED", "REVIEW_QUEUE"] else corr.extracted_refdes
            enriched["spec_value"] = corr.spec_value
            enriched["correction_status"] = corr.status
            enriched["correction_dist"] = corr.distance
            enriched["correction_conf"] = corr.confidence
            results.append(enriched)

        return results
