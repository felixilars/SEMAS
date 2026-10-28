"""
Layout Analysis & Tabular Extraction Package
=============================================
Provides automated column gutter detection, token coalescing, reference designator expansion, and tabular BOM component extraction.
"""

from src.layout.gutter_detector import find_column_slices
from src.layout.token_coalescer import coalesce_adjacent_tokens
from src.layout.refdes_expander import expand_refdes_token
from src.layout.bom_parser import (
    BOMTableParser,
    BOMParser,
    is_spec_unit,
    extract_specification_fields,
)

__all__ = [
    "find_column_slices",
    "coalesce_adjacent_tokens",
    "expand_refdes_token",
    "BOMTableParser",
    "BOMParser",
    "is_spec_unit",
    "extract_specification_fields",
]
