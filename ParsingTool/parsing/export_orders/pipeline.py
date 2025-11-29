"""Export-orders pipeline using shared EXPORT_FIELD_PATTERNS.

This module parses an export-order PDF into a one-row CSV (or multi-row when
there are multiple batch numbers). It relies on the shared EXPORT_FIELD_PATTERNS
so that the regex definitions are centralised and consistent with the simple
`parse_pdf` helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import re

import pandas as pd

from ..shared.pdf_utils import extract_text
from ..shared.export_patterns import EXPORT_FIELD_PATTERNS
from ..qc import EXPECTED_COLUMNS

# Backwards-compat alias: some existing code may still import FIELD_PATTERNS
FIELD_PATTERNS = EXPORT_FIELD_PATTERNS

FLAGS = re.IGNORECASE | re.MULTILINE


def _find_line(pattern: str, text: str) -> str:
    """Return the first capture group for the given pattern in the text."""
    match = re.search(pattern, text, FLAGS)
    return match.group(1).strip() if match else ""


def parse_export_text(text: str) -> Dict[str, Any]:
    """Parse raw PDF text into a dict of field -> value using shared patterns."""
    return {
        field: _find_line(pattern, text)
        for field, pattern in FIELD_PATTERNS.items()
    }


def _extract_text_compat(path: str, debug: bool, use_ocr: bool) -> str:
    """Call `extract_text` but stay compatible with simple monkeypatched fakes."""
    try:
        return extract_text(path, debug=debug, use_ocr=use_ocr)
    except TypeError:
        # Likely a simple fake/monkeypatch that only takes `path`.
        return extract_text(path)


def parse_export_pdf(
    pdf_path: Path | str,
    debug: bool = False,
    use_ocr: bool = False,
) -> pd.DataFrame:
    """Parse a single export-order PDF into a DataFrame.

    - Container-level / header fields come from shared regex patterns
      plus a few overrides.
    - One row is produced per Batch Number found in the text.
    """

    pdf_path = Path(pdf_path)
    text = _extract_text_compat(str(pdf_path), debug=debug, use_ocr=use_ocr)

    # First pass: use the shared regex patterns
    fields = parse_export_text(text)

    # -----------------------------------------------------------
    # Overwrite the tricky fields based on this packing layout
    # -----------------------------------------------------------

    # 1) SSCC Qty  -> line like "22.000 PAL"
    # Anchor to the start of a line so we don't swallow batch digits above.
    m = re.search(r"^\s*([\d., ]+)\s+PAL\b", text, FLAGS)
    if m:
        qty_raw = m.group(1)
        qty_clean = re.sub(r"\s+", "", qty_raw).strip()
        fields["SSCC Qty"] = f"{qty_clean} PAL"

    # 2) 3rd Party Storage  -> Packer line
    # Capture 1 or 2 lines to handle wrapped names, but stop if we hit Consignee
    m = re.search(r"Packer\s*:\s*\n([^\n]+(?:\n[^\n]+)?)", text, FLAGS)
    if m:
        raw = m.group(1)
        # If we accidentally captured the start of "Consignee :", cut it off
        if "Consignee" in raw:
            raw = raw.split("Consignee")[0]
        fields["3rd Party Storage"] = raw.replace("\n", " ").strip()

    # 3) Variety / Grade / Size / Packaging from description line
    #    We look for a line that starts with "Almonds" and then decide
    #    whether it's a normal product (has size 25/27 etc.) or a rejects
    #    product (no size; contains Non Var / Mfg / Splits / etc.).

    REJECT_TOKENS = (
        "non var",
        "mfg",
        "splits",
        "brokens",
        "splits&brokens",
        "beltuza",
        "satake",
        "h&s",
    )

    # -----------------------------------------------------------
    # Product Description Search (with fallbacks for OCR)
    # -----------------------------------------------------------
    
    desc_match = None
    
    # 1. Primary: Standard "Almonds ..."
    if not desc_match:
        desc_match = re.search(r"(Almonds[^\n]+)", text, FLAGS)
        
    # 2. Fallback (Typos): "AImonds", "Kern", "ALM" (word boundary)
    if not desc_match:
        desc_match = re.search(r"((?:A[lI]monds|Kern|\bALM\b)[^\n]+)", text, FLAGS)
        
    # 3. Fallback (Context): Look for size pattern like "25/27"
    if not desc_match:
        desc_match = re.search(r"([^\n]*\d{2}\s*/\s*\d{2}[^\n]*)", text, FLAGS)

    # 4. Fallback (Keywords): Stockfeed, Mfr, etc.
    if not desc_match:
        desc_match = re.search(r"((?:Stockfeed|Mfr|Manufacturing|Inshell|Hulls)[^\n]+)", text, FLAGS)

    if desc_match:
        desc = desc_match.group(1).strip()
        desc_lower = desc.lower()

        # Does this line contain a size like 25/27, 30 / 32, etc.?
        has_size = re.search(r"\d{2}\s*/\s*\d{2}", desc)

        is_reject = (not has_size) and any(tok in desc_lower for tok in REJECT_TOKENS)
        # Also treat the new fallback keywords as rejects if they don't have a size
        if not is_reject and not has_size:
             is_reject = any(k in desc_lower for k in ["stockfeed", "mfr", "manufacturing", "inshell", "hulls"])

        if is_reject:
            # REJECTS PRODUCT
            # Variety: up to "Non Var" if present, otherwise use a default.
            var_match = re.search(r"^(Almonds\s+Kern\s+Non\s+Var)", desc, FLAGS)
            if var_match:
                variety = var_match.group(1).strip()
                rest = desc[var_match.end():].strip()
            else:
                variety = "Almonds Kern Non Var"
                rest = desc

            # Fix Grade Bleeding: Split Grade from Packaging if units are found
            # e.g. "Std Gr 850KG bag" -> Grade="Std Gr", Packaging="850KG bag"
            packaging = "Bulk Bags" # default
            
            # Look for a unit like KG, lb, bag, T
            unit_match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:KG|lb|T)|bag)\b", rest, re.IGNORECASE)
            if unit_match:
                split_idx = unit_match.start()
                # The part starting from the unit is the packaging
                packaging = rest[split_idx:].strip()
                # The part before is the grade
                rest = rest[:split_idx].strip()

            # Remove a trailing "KG" from grade part if it was left over (legacy check)
            rest = re.sub(r"\bKG\b", "", rest, flags=re.IGNORECASE).strip()

            fields["Variety"] = variety.title()      # Normalize case
            fields["Grade"]   = rest
            fields["Size"]    = "N/A"
            fields["Packaging"] = packaging
        else:
            # NORMAL PRODUCT (with size)
            # Example: "Almonds Kern Carm Supr 25/27 50lb ctn"
            m = re.search(
                r"(Almonds\s+Kern\s+\w+)\s+(\w+)\s+(\d{2}\s*/\s*\d{2})\s+(\d+\s*lb\s+\w+)",
                desc,
                FLAGS,
            )
            if m:
                variety, grade, size, packaging = [s.strip() for s in m.groups()]
                fields["Variety"]   = variety.title() # Normalize case
                fields["Grade"]     = grade
                fields["Size"]      = size
                fields["Packaging"] = packaging

    # 4) Pallet  -> "PLASTIC export pallets", "fibre export pallets", etc.
    m = re.search(r"loaded on\s+([A-Za-z ]+pallets)", text, FLAGS)
    if m:
        fields["Pallet"] = m.group(1).strip()

    # 5) Fumigation -> "2 days Fumigation with Profume"
    fum_value: str | None = None

    # First try the explicit "<n> days Fumigation ..." pattern.
    m = re.search(r"(\d+\s+days\s+Fumigation[^\n]*)", text, FLAGS)
    if m:
        fum_value = m.group(1).strip()
    else:
        # Fallback: use the last line that contains the word "Fumigation".
        matches = re.findall(r"[^\n]*Fumigation[^\n]*", text, FLAGS)
        if matches:
            fum_value = matches[-1].strip()

    if fum_value:
        fields["Fumigation"] = fum_value

    # -----------------------------------------------------------
    # Build rows: one per Batch Number if we can find them
    # -----------------------------------------------------------

    # Per-line bag counts for rejects, e.g. "14 BAGS", "3 BAGS".
    bag_counts_raw = re.findall(r"(\d[\d\.,]*)\s+BAGS\b", text, FLAGS)
    bag_counts = [re.sub(r"\s+", "", b).strip() for b in bag_counts_raw]
    bag_idx = 0

    # Per-line pallet counts for normal product, e.g. "22.000 PAL"
    pal_counts_raw = re.findall(r"([\d., ]+)\s+PAL\b", text, FLAGS)
    pal_counts = [re.sub(r"\s+", "", p).strip() for p in pal_counts_raw]
    pal_idx = 0

    # Per-line reject grades, e.g. "H&S Satake", "H&S Beltuza"
    reject_grades = re.findall(r"(H&S\s+[A-Za-z]+)", text, FLAGS)
    grade_idx = 0

    # Find all batch numbers like "Batch : F012322001".
    batch_numbers = re.findall(r"Batch\s*:\s*([A-Z0-9]+)", text, FLAGS)

    rows: list[list[str]] = []

    if batch_numbers:
        # dict.fromkeys(...) keeps order but removes exact duplicates.
        for batch in dict.fromkeys(batch_numbers):
            row_fields = dict(fields)
            row_fields["Batch Number"] = batch

            if row_fields.get("Packaging") == "Bulk Bags":
                # REJECTS ROW: use BAGS and per-line H&S <something> grade
                if bag_idx < len(bag_counts):
                    row_fields["SSCC Qty"] = f"{bag_counts[bag_idx]} BAGS"
                    bag_idx += 1

                if grade_idx < len(reject_grades):
                    row_fields["Grade"] = reject_grades[grade_idx]
                    grade_idx += 1
            else:
                # NORMAL ROW: use per-line PAL quantity if available
                if pal_idx < len(pal_counts):
                    row_fields["SSCC Qty"] = f"{pal_counts[pal_idx]} PAL"
                    pal_idx += 1

            row = [row_fields.get(column, "") for column in EXPECTED_COLUMNS]
            rows.append(row)
    else:
        # Fallback: just one row like before.
        row = [fields.get(column, "") for column in EXPECTED_COLUMNS]
        rows.append(row)

    df = pd.DataFrame(rows, columns=EXPECTED_COLUMNS)
    df = df.drop_duplicates().reset_index(drop=True)
    return df


def run(*, input_pdf: str, out: str, use_ocr: bool = False) -> None:
    df = parse_export_pdf(input_pdf, use_ocr=use_ocr)
    df.to_csv(out, index=False)
