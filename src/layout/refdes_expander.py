"""
Reference Designator Range Expander Module
==========================================
Expands compressed, hyphenated, or comma-delimited reference designator groups into canonical individual component identifiers (e.g. 'R101-105' into individual resistor identifiers from R101 to R105).
"""

from pathlib import Path
import re


def expand_refdes_token(token_text, default_prefix=None, max_span=50):
    """ Expand a single grouped or hyphenated token into individual RefDes strings.

    Args:
      - token_text (str) : Raw candidate string (e.g. 'R101-104', 'C101, 102').
      - default_prefix (str or None) : Inherited letter prefix if available.
      - max_span (int) : Maximum numeric range spread permitted as safety guard.
    Returns: List of expanded individual uppercase RefDes strings.
    """
    if not token_text:
        return []

    # Clean whitespace and normalize hyphens/tildes to standard ASCII minus
    cleaned = str(token_text).strip().upper()
    cleaned = re.sub(r"[\s]", "", cleaned)
    cleaned = re.sub(r"[\u2013\u2014~]", "-", cleaned)

    # Case 1: Comma-delimited sequence, e.g. 'C101, 102, 103' or 'R101-103, 105'
    if "," in cleaned:
        tokens = cleaned.split(",")
        results = []
        active_prefix = default_prefix

        for part in tokens:
            part = part.strip()
            if not part:
                continue

            sub_items = expand_refdes_token(part, default_prefix=active_prefix, max_span=max_span)
            if sub_items:
                # Update active prefix if any expanded sub-item starts with letters
                first_match = re.match(r"^([A-Z]{1,3})\d+", sub_items[0])
                if first_match:
                    active_prefix = first_match.group(1)
                results.extend(sub_items)

        return results

    # Case 2: Hyphenated range, e.g. 'R101-R104', 'R101-104', 'U29-30'
    range_match = re.match(r"^([A-Z]{1,3})?(\d+)-(?:[A-Z]{1,3})?(\d+)$", cleaned)
    if range_match:
        explicit_prefix = range_match.group(1)
        prefix = explicit_prefix if explicit_prefix else default_prefix

        if prefix:
            start_idx = int(range_match.group(2))
            end_idx = int(range_match.group(3))

            # Validate range ordering and apply safety guard
            if start_idx <= end_idx:
                span = end_idx - start_idx
                if span <= max_span:
                    expanded = []
                    start_str = range_match.group(2)
                    orig_len = len(start_str)
                    has_leading_zero = start_str.startswith("0") and orig_len > 1

                    for num in range(start_idx, end_idx + 1):
                        if has_leading_zero:
                            expanded.append(prefix + str(num).zfill(orig_len))
                        else:
                            expanded.append(prefix + str(num))
                    return expanded
                else:
                    print("[WARN] Range span " + str(span) + " exceeds max safety threshold (" + str(max_span) + ") for: " + cleaned)
                    return [cleaned]

    # Case 3: Inherit prefix for standalone numeric index, e.g. '102' with active_prefix 'C'
    if cleaned.isdigit() and default_prefix:
        return [default_prefix + cleaned]

    # Case 4: Standalone standard token without range syntax
    return [cleaned]
