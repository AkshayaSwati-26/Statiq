"""
ingestion/parser.py
===================
Fixed-width microdata parser module.
Wraps and exposes parsing logic from fwf_parser.py.
"""

from ingestion.fwf_parser import (
    parse_layout_excel,
    parse_codes_excel,
    read_fwf_level,
    read_fwf_from_bytes,
    apply_codebook_labels,
    cast_types
)
