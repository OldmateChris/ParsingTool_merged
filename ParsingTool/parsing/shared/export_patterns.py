"""Shared regular expression patterns for export-order PDFs.

This module centralises the field name -> regex mapping so that both the
export pipeline and any simple parsers (for example GUI helpers) can use the
same, canonical definitions.

Each pattern is expected to contain exactly one *capturing group* which
represents the value to extract from the line.
"""

from __future__ import annotations

from typing import Dict

# Matches the rest of a line after the label (non-newline characters)
LINE = r"([^\n]+)"

EXPORT_FIELD_PATTERNS: Dict[str, str] = {


    # The PDF uses "Date" not always "Date Requested"
    "Date Requested": r"D[a@]te\s*(?:R[e3]qu[e3]st[e3]d)?[\s:.-]*([\d./-]+)",

    # OLAM Ref No. / OLAM Ref Number
    "OLAM Ref Number": r"OLAM\s*Ref\s*(?:No\.?|Number)[\s:]*([\w-]+)",

    # Delivery No. / Delivery Number
    "Delivery Number": r"D[eIl]livery\s*(?:N[o0]\.?|N[u]mb[e3]r)?[\s:.-]*([\w-]+)",

    # Sale Order No. / Sale Order Number
    "Sale Order Number": r"S[a@]le\s*Ord[e3]r\s*(?:N[o0]\.?|N[u]mb[e3]r)?[\s:.-]*([\w-]+)",

    # Batch number / Batch No. — allow split label + value
    "Batch Number": r"B[a@]tch\s*(?:N[o0]\.?|N[u]mb[e3]r)?[\s:.-]*([\w\-\/]+)",
    
    # SSCC quantity
    "SSCC Qty": r"SSCC\s*Qty[\s:]*([\d,\.]+)",

    # Vessel ETD, allowing for `Vessel ETD\n:\n16.07.2025`
    "Vessel ETD": r"Vessel\s*ETD[\s:]*([\w\-/\.]+)",

    # Final Destination / Destination
    "Destination": rf"(?:Final\s+Destination|Destination)[\s:]*{LINE}",

    # 3rd Party Storage text on same line or following line
    "3rd Party Storage": r"^\s*3rd\s*Party\s*Storage\b[\s:]*([^\n]+)",
    
    # Variety / Grade / Size / Packaging / Pallet / Fumigation
    # These are usually simple labels with text after them
    "Variety":           r"^\s*Variety\b[\s:]*([^\n]+)",
    "Grade":             r"^\s*Grade\b[\s:]*([A-Za-z0-9/ +\.-]+)",
    "Size":              r"^\s*Size\b[\s:]*([A-Za-z0-9/ +\.-]+)",
    "Packaging":         r"^\s*Packaging\b[\s:]*([^\n]+)",
    "Pallet":            r"^\s*Pallet\b[\s:]*([A-Za-z0-9\-]+)",
    "Fumigation":        r"^\s*Fumigation\b[\s:]*([^\n]+)",


    # Container Size
    #   Container Size
    #   : Container (40ft) X 1 Food Quality
    "Container": r"Container\s*Size[\s:]*([^\n]+)",
}


