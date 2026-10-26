"""
Unit Tests for Reference Designator Expander
=============================================
Tests range expansion, comma-delimited list expansion, prefix inheritance,
and range safety thresholds.
"""

import sys
from pathlib import Path
import pytest

sys.path.append(str(Path(__file__).parent.parent))

from src.layout.refdes_expander import expand_refdes_token


def test_expand_hyphenated_range():
    """ Verify numeric range expansion across standard formats."""
    assert expand_refdes_token("R101-105") == ["R101", "R102", "R103", "R104", "R105"]
    assert expand_refdes_token("R101-R104") == ["R101", "R102", "R103", "R104"]
    assert expand_refdes_token("U29-30") == ["U29", "U30"]
    assert expand_refdes_token("R01-05") == ["R01", "R02", "R03", "R04", "R05"]


def test_expand_dash_and_whitespace_variants():
    """ Verify handling of en-dash, em-dash, tilde, and spaces."""
    assert expand_refdes_token("R101 - 103") == ["R101", "R102", "R103"]
    assert expand_refdes_token("R101\u2013103") == ["R101", "R102", "R103"]  # En-dash
    assert expand_refdes_token("R101\u2014103") == ["R101", "R102", "R103"]  # Em-dash
    assert expand_refdes_token("R101~103") == ["R101", "R102", "R103"]


def test_expand_comma_delimited_list():
    """ Verify prefix inheritance across comma-separated elements."""
    assert expand_refdes_token("C101, 102, 103") == ["C101", "C102", "C103"]
    assert expand_refdes_token("R101, R102, R103") == ["R101", "R102", "R103"]
    assert expand_refdes_token("C101, 102-104") == ["C101", "C102", "C103", "C104"]


def test_expand_single_tokens():
    """ Verify standalone tokens pass through intact."""
    assert expand_refdes_token("Q701") == ["Q701"]
    assert expand_refdes_token("IC01") == ["IC01"]
    assert expand_refdes_token("") == []
    assert expand_refdes_token(None) == []


def test_expand_safety_bounds():
    """ Verify safety guard on excessive spans and invalid range bounds."""
    # Exceeds max_span=50
    oversized = expand_refdes_token("R101-9999", max_span=50)
    assert oversized == ["R101-9999"]

    # Inverted range
    inverted = expand_refdes_token("R105-101")
    assert inverted == ["R105-101"]
