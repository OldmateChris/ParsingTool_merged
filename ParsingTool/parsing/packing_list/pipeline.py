"""Packing List (PI) pipeline.

Specialised for '_PI.pdf' files which explicitly list PAL quantities
and have a cleaner 'Packer' layout than ZAPI files.
"""
from __future__ import annotations
from pathlib import Path

import re
import pandas as pd

from ..shared.pdf_utils import extract_text
from ..shared.export_patterns import EXPORT_FIELD_PATTERNS
from ..qc import EXPECTED_COLUMNS
from ..export_orders.pipeline import parse_product_line


# Reuse your shared patterns
FIELD_PATTERNS = EXPORT_FIELD_PATTERNS
FLAGS = re.IGNORECASE | re.MULTILINE

def _find_line(pattern: str, text: str) -> str:
    """Helper to find a single value using a regex pattern."""
    match = re.search(pattern, text, FLAGS)
    if match:
        val = match.group(1).strip()
        # Filter out common header noise if the regex grabs the label itself
        if val.lower() in ["sale", "date", "delivery", "booking", "quantity", "description"]:
            return ""
        return val
    return ""

def parse_pi_pdf(
    pdf_path: Path | str,
    debug: bool = False,
    use_ocr: bool = False,
) -> pd.DataFrame:
    pdf_path = Path(pdf_path)
    text = extract_text(str(pdf_path), debug=debug, use_ocr=use_ocr)

    fields: dict[str, str] = {}

    # 1. Standard Fields (Headers) using shared patterns
    for field, pattern in FIELD_PATTERNS.items():
        fields[field] = _find_line(pattern, text)

    # 2. PI-Specific: Explicit Pallet Count (e.g. "22.000 PAL")
    pal_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s+PAL\b", text, FLAGS)
    if pal_match:
        fields["SSCC Qty"] = f"{pal_match.group(1).strip()} PAL"

    # 3. PI-Specific: Packer -> 3rd Party Storage
    packer_match = re.search(r"Packer\s*[:\s]*\n([^\n]+)", text, FLAGS)
    if packer_match:
        val = packer_match.group(1).strip()
        if "Seaway" in val or "RJN" in val or "Olam" in val:
            fields["3rd Party Storage"] = val

    # 3b. Destination, Pallet, Fumigation

    # Destination – PI-specific first, then fallback to export pattern
    # 1) Prefer "Final Destination : ..." if it exists on a single line
    m = re.search(r"Final\s+Destination\s*:\s*([^\n]+)", text, FLAGS)
    if m:
        fields["Destination"] = m.group(1).strip()
    else:
        # 1b) If label and value are on separate lines
        m = re.search(r"Final\s+Destination\s*:[^\n]*\n([^\n]+)", text, FLAGS)
        if m:
            fields["Destination"] = m.group(1).strip()
        else:
            # 2) Otherwise, look for a plain "Destination : ..."
            m = re.search(r"\bDestination\s*:\s*([^\n]+)", text, FLAGS)
            if m:
                fields["Destination"] = m.group(1).strip()
            else:
                # 3) Last resort: use export's Destination pattern,
                #    but ignore lines that are actually "Shipping Line"
                dest_pat = EXPORT_FIELD_PATTERNS.get("Destination")
                if dest_pat:
                    dest_val = _find_line(dest_pat, text)
                    if dest_val and not dest_val.strip().startswith("Shipping Line"):
                        fields["Destination"] = dest_val.strip()

    # Pallet – e.g. "PLASTIC export pallets", "fibre export pallets"
    m = re.search(r"loaded on\s+([A-Za-z ]+pallets?)", text, FLAGS)
    if m:
        fields["Pallet"] = m.group(1).strip()

    # If no pallet type but instructions say hand stacked, mark it
    if "Pallet" not in fields or not fields["Pallet"]:
        if re.search(r"hand\s+stacked", text, FLAGS):
            fields["Pallet"] = "Hand stacked (no pallets)"

    # Fumigation – e.g. "2 days Fumigation with Profume"
    m = re.search(r"(\d+\s+days\s+Fumigation[^\n]*)", text, FLAGS)
    if m:
        fields["Fumigation"] = m.group(1).strip()
    else:
        # Fallback: last line in the document containing the word Fumigation
        matches = re.findall(r"[^\n]*Fumigation[^\n]*", text, FLAGS)
        if matches:
            fields["Fumigation"] = matches[-1].strip()

    # 4. Product Description – reuse export product parser
    # Find the first line that looks like a product description
    desc_match = re.search(
        r"^.*(?:Almonds|Alm|Kern|Inshell).*$", text, FLAGS | re.MULTILINE
    )
    if desc_match:
        parsed = parse_product_line(desc_match.group(0))
        # Copy the parsed fields into our fields dict
        for key in ("Variety", "Grade", "Size", "Packaging"):
            if parsed.get(key):
                fields[key] = parsed[key]

    # 4b. FINAL override for Destination from any 'Final Destination' line
    final_dest_match = re.search(r"Final\s+Destination[^\n]*", text, FLAGS)
    if final_dest_match:
        line = final_dest_match.group(0)
        value = re.sub(r"(?i)final\s+destination\s*:?", "", line).strip(" -:\t")
        if value:
            fields["Destination"] = value

    # 5. Build Row(s) and return DataFrame
    row = [fields.get(c, "") for c in EXPECTED_COLUMNS]
    return pd.DataFrame([row], columns=EXPECTED_COLUMNS)

def run(
    *,
    input_pdf: str,
    out: str,
    use_ocr: bool = False,
    debug: bool = False,
) -> None:
    df = parse_pi_pdf(input_pdf, use_ocr=use_ocr, debug=debug)
    df.to_csv(out, index=False)
    if debug:
        print(f"Processed PI: {input_pdf}")

def run_batch(
    input_dir: Path,
    output_dir: Path,
    *,
    use_ocr: bool = False,
    debug: bool = False,
) -> None:
    """
    Batch-process PI / packing list PDFs in `input_dir` and write
    a single combined CSV to `output_dir/pi_combined.csv`.
    """
    out_file = output_dir / "pi_combined.csv"

    pdf_files = sorted(input_dir.glob("*.pdf"))
    print(f"[PI] Found {len(pdf_files)} PDFs in {input_dir}")

    all_dfs: list[pd.DataFrame] = []
    for pdf in pdf_files:
        try:
            # Note: parse_pi_pdf signature: (pdf_path, debug=False, use_ocr=False)
            df = parse_pi_pdf(pdf, use_ocr=use_ocr, debug=debug)
            df["Source_File"] = pdf.name
            all_dfs.append(df)
        except Exception as e:
            print(f"[PI] ERROR processing {pdf.name}: {e}")

    if not all_dfs:
        print("[PI] No data collected.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)
    combined.to_csv(out_file, index=False)
    print(f"[PI] Wrote combined CSV: {out_file}")

def parse_packing_list_pdf(
    pdf_path: Path | str,
    use_ocr: bool = False,
    debug: bool = False,
) -> pd.DataFrame:
    """
    Compatibility wrapper so the batch runner can call the PI parser
    as `parse_packing_list_pdf(...)`.
    """
    return parse_pi_pdf(pdf_path, debug=debug, use_ocr=use_ocr)
