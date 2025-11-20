from __future__ import annotations
import re
from typing import Dict, List

from ..shared.pdf_utils import extract_text
from ..shared.csv_writer import write_csv
from ..shared.schemas import EXPORT_COLUMNS

LINE = r"([^\n]+)"  # helper for 'rest of line'

FIELD_PATTERNS: Dict[str, str] = {
    "Name": rf"^\s*Name[:\s]+{LINE}$",
    "Date Requested": r"^\s*Date\s*Requested[:\s]+([\d\-/]+)$",
    "Delivery Number": r"^\s*Delivery\s*Number[:\s]+([\w-]+)$",
    "Sale Order Number": r"^\s*Sale\s*Order\s*Number[:\s]+([\w-]+)$",
    "Batch Number": r"^\s*Batch\s*Number[:\s]+([\w-]+)$",
    "SSCC Qty": r"^\s*SSCC\s*Qty[:\s]+([\w-]+)$",
    "Vessel ETD": r"^\s*Vessel\s*ETD[:\s]+([\w\-/]+)$",
    "Destination": rf"^\s*Destination[:\s]+{LINE}$",
    "3rd Party Storage": rf"^\s*3rd\s*Party\s*Storage[:\s]+{LINE}$",
    "Variety": rf"^\s*Variety[:\s]+{LINE}$",
    "Grade": r"^\s*Grade[:\s]+([\w]+)$",
    "Size": r"^\s*Size[:\s]+([\w/]+)$",
    "Packaging": rf"^\s*Packaging[:\s]+{LINE}$",
    "Pallet": r"^\s*Pallet[:\s]+([\w-]+)$",
    "Fumigation": rf"^\s*Fumigation[:\s]+{LINE}$",
    "Container": r"^\s*Container[:\s]+([\w-]+)$",
}

def _find_line(pattern: str, text: str) -> str:
    m = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    return (m.group(1).strip() if m else "")

def _parse_fields(text: str) -> Dict[str, str]:
    return {k: _find_line(pat, text) for k, pat in FIELD_PATTERNS.items()}

def run(*, input_pdf: str, out: str) -> None:
    """
    Export pipeline: parse one Export-style PDF -> one-row CSV with EXPORT_COLUMNS.
    """
    text = extract_text(input_pdf)
    fields = _parse_fields(text)

    row = {col: fields.get(col, "") for col in EXPORT_COLUMNS}
    write_csv(out, [row], EXPORT_COLUMNS)
