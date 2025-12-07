"""Export-orders pipeline using shared EXPORT_FIELD_PATTERNS.

This version includes:
1. Token Plucking for robust Product parsing.
2. Enhanced 3rd Party Storage parsing with stricter stop-words and case-insensitive fallback.
3. Strategy C for bulk/reject loads.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import re
import pandas as pd
from ..shared.pdf_utils import extract_text
from ..shared.export_patterns import EXPORT_FIELD_PATTERNS
from ..qc import EXPECTED_COLUMNS

# --- Configuration ---

FIELD_PATTERNS = EXPORT_FIELD_PATTERNS
FLAGS = re.IGNORECASE | re.MULTILINE

KNOWN_GRADES = [
    "SSR", "Supr", "XNo1", "XNo.1", "X No 1", "X No.1", 
    "Premium", "Supreme", "Select", "Std", "Standard",
    "Mfr", "Manufacturing", "H&S", "Rejects", "Mixed",
    "Carm", "Nonpareil" 
]

def _find_line(pattern: str, text: str) -> str:
    match = re.search(pattern, text, FLAGS)
    if match:
        val = match.group(1).strip()
        if val.lower() in ["sale", "date", "delivery", "booking", "quantity", "description"]:
            return ""
        return val
    return ""

def parse_product_line(line: str) -> Dict[str, str]:
    """Smarter parsing: Pluck out known tokens, leave the rest as Variety."""
    row = {"Variety": "", "Grade": "", "Size": "N/A", "Packaging": ""}
    
    # 1. Remove leading material codes immediately
    remainder = re.sub(r"^\s*\d+[\s/]+", "", line.strip())

    # 2. PLUCK SIZE
    size_match = re.search(r"\b(\d{2}\s*/\s*\d{2})\b", remainder)
    if size_match:
        row["Size"] = size_match.group(1).replace(" ", "")
        remainder = remainder.replace(size_match.group(0), " ")

    # 3. PLUCK PACKAGING
    pack_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*(lb|kg|g|oz|T|b)\b\s*([a-zA-Z]*)", remainder, re.IGNORECASE)
    if pack_match:
        full_pack = pack_match.group(0).strip()
        if "50b" in full_pack.lower() and "ctn" in full_pack.lower():
            full_pack = full_pack.replace("50b", "50lb")
        row["Packaging"] = full_pack
        remainder = remainder.replace(pack_match.group(0), " ")
    elif "bulk bags" in remainder.lower():
        row["Packaging"] = "Bulk Bags"
        remainder = re.sub(r"\bBulk Bags\b", " ", remainder, flags=re.IGNORECASE)

        # 3.5 SPECIAL CASE: Splits & Broken is a Grade
    splits_pattern = re.compile(r"splits\s*&\s*broken|splits&broken", re.IGNORECASE)
    if splits_pattern.search(remainder):
        # Set the grade
        row["Grade"] = "Splits & Broken"
        # Remove that phrase from the remainder so Variety is cleaner
        remainder = splits_pattern.sub(" ", remainder)

        # 3.6 SPECIAL CASE: Mfg Gr is also a Grade
    mfg_pattern = re.compile(r"\bmfg\s*gr\b", re.IGNORECASE)
    if mfg_pattern.search(remainder):
        row["Grade"] = "Mfg Gr"
        remainder = mfg_pattern.sub(" ", remainder)

        # 3.7 SPECIAL CASE: Satake is a Grade (H&S Satake)
    satake_pattern = re.compile(r"\bsatake\b", re.IGNORECASE)
    if satake_pattern.search(remainder):
        row["Grade"] = "H&S Satake"
        remainder = satake_pattern.sub(" ", remainder)

    # 3.8 SPECIAL CASE: Helius is a Grade (H&S Helius)
    helius_pattern = re.compile(r"\bhelius\b", re.IGNORECASE)
    if helius_pattern.search(remainder):
        row["Grade"] = "H&S Helius"
        remainder = helius_pattern.sub(" ", remainder)


    # 4. PLUCK GRADE
    if not row["Grade"]:
        for grade in sorted(KNOWN_GRADES, key=len, reverse=True):
            pattern = r"\b" + re.escape(grade) + r"\b"
            if re.search(pattern, remainder, re.IGNORECASE):
                row["Grade"] = grade
                remainder = re.sub(pattern, " ", remainder, flags=re.IGNORECASE)
                break

    # 5. CLEANUP VARIETY
    remainder = re.sub(r"\b\d{2,}\.\d+\.\d+\b", " ", remainder)
    remainder = re.sub(r"\b\d{3,}\b", " ", remainder) 
    remainder = re.sub(r"\bX\b", " ", remainder, flags=re.IGNORECASE)

    cleaned_var = re.sub(r"\s+", " ", remainder).strip(" ,.-")
    row["Variety"] = cleaned_var.title() if cleaned_var else ""
    
    return row

def parse_export_pdf(
    pdf_path: Path | str,
    debug: bool = False,
    use_ocr: bool = False,
) -> pd.DataFrame:
    pdf_path = Path(pdf_path)
    try:
        text = extract_text(str(pdf_path), debug=debug, use_ocr=use_ocr)
    except TypeError:
        text = extract_text(str(pdf_path))

    fields = {}
    
    # 1. Standard Fields
    for field, pattern in FIELD_PATTERNS.items():
        val = _find_line(pattern, text)
        if field in ["Delivery Number", "Sale Order Number", "OLAM Ref Number", "Batch Number"]:
            if val and not any(c.isdigit() for c in val):
                val = ""
        fields[field] = val
    
    if debug and not fields.get("Delivery Number"):
        print(f"[WARN] {pdf_path.name}: Could not find 'Delivery Number' using regex.")

    # 2. OVERRIDES & FIXES
    
    # SSCC Qty
    m = re.search(r"\b(\d+(?:[.,]\d+)?)\s+PAL\b", text, FLAGS)
    if m:
        fields["SSCC Qty"] = f"{m.group(1).strip()} PAL"

    # --- 3rd Party Storage (Packer) Fix ---
    packer_val = ""
    # Regex: Look for Packer, capture line(s) until we hit a stop word or double newline
    m = re.search(r"Packer\s*[:\s]*\s*([^\n]+(?:(?:\n(?!Consignee|Notify|Delivery|Sale)[^\n]+))?)", text, FLAGS)
    if m:
        raw = m.group(1)
        # Aggressive Stop List: Now includes OLAM, Ref, Booking to prevent capturing headers
        stops = r"(?i)\b(?:Consignee|Notify|Delivery|Sale|Date|OLAM|Ref|Booking|Container)\b"
        raw = re.split(stops, raw)[0]
        
        cleaned = raw.replace("\n", " ").strip()
        
        # Validation: Must have letters and NOT be just digits/symbols
        if re.search(r"[A-Za-z]{2,}", cleaned) and not re.match(r"^[\d\s\W]+$", cleaned):
            packer_val = cleaned

    # Fallback Heuristic (Case-Insensitive)
    if not packer_val:
        text_lower = text.lower()
        if "seaway" in text_lower: packer_val = "Seaway Intermodal Pty Ltd"
        elif "rjn" in text_lower: packer_val = "RJN Storage and Logistics Pty Ltd"
        elif "west melbourne" in text_lower: packer_val = "West Melbourne Processing Plant-OOA"
    
    fields["3rd Party Storage"] = packer_val

    # Pallet
    m = re.search(r"loaded on\s+([A-Za-z ]+pallets)", text, FLAGS)
    if m: fields["Pallet"] = m.group(1).strip()

    # Fumigation
    m = re.search(r"(\d+\s+days\s+Fumigation[^\n]*)", text, FLAGS)
    if m: fields["Fumigation"] = m.group(1).strip()
    else:
        matches = re.findall(r"[^\n]*Fumigation[^\n]*", text, FLAGS)
        if matches: fields["Fumigation"] = matches[-1].strip()

    # 3. PRODUCT DESCRIPTION
    candidate_line = ""
    
    # Strategy A: Explicit Product
    match = re.search(r"^.*(?:Almonds|Kern|Alm\b|Inshell).*$", text, FLAGS)
    if match: candidate_line = match.group(0)

    # Strategy B: Size Pattern
    if not candidate_line:
        match = re.search(r"^.*\d{2}\s*/\s*\d{2}.*$", text, FLAGS)
        if match: candidate_line = match.group(0)

    # Strategy C: Rejects/Bulk Hunter
    if not candidate_line:
        match = re.search(r"^.*(?:H&S|Mfg|Bulk Bags|Splits).*$", text, FLAGS)
        if match: candidate_line = match.group(0)

    # Validation: Kill line if it looks like just numbers
    if candidate_line:
        clean_check = re.sub(r"^\s*\d+[\s/]+", "", candidate_line)
        if not re.search(r"[A-Za-z]{3,}", clean_check):
            candidate_line = ""

    # Parse what we found
    product_info = {"Variety": "", "Grade": "", "Size": "", "Packaging": ""}
    if candidate_line:
        product_info = parse_product_line(candidate_line)
        fields.update(product_info)
    
    # Final Scrub: If Variety is still garbage, wipe it.
    if re.match(r"^[\d\s\.,/]+[A-Za-z]{0,2}$", fields.get("Variety", "")):
        fields["Variety"] = ""

    # 4. BATCH ROWS
    bag_counts = re.findall(r"(\d[\d\.,]*)\s+BAGS\b", text, FLAGS)
    pal_counts = re.findall(r"\b(\d+(?:[.,]\d+)?)\s+PAL\b", text, FLAGS)
    batch_numbers = re.findall(r"Batch\s*:\s*([A-Z0-9]+)", text, FLAGS)
    reject_grades = re.findall(r"(H&S\s+[A-Za-z]+)", text, FLAGS)

    rows = []
    bag_idx, pal_idx, grade_idx = 0, 0, 0

    if batch_numbers:
        seen = set()
        unique_batches = [x for x in batch_numbers if not (x in seen or seen.add(x))]

        # Alignment Check
        if len(bag_counts) > 0 and len(bag_counts) != len(unique_batches):
            print(f"Warning: Found {len(bag_counts)} bag counts but {len(unique_batches)} unique batches. Data may be misaligned.")

        for batch in unique_batches:
            row = dict(fields)
            row["Batch Number"] = batch
            is_bulk = "bag" in str(row.get("Packaging", "")).lower() or not row.get("Size") or row.get("Size") == "N/A"
            
            if is_bulk:
                if bag_idx < len(bag_counts):
                    row["SSCC Qty"] = f"{bag_counts[bag_idx]} BAGS"
                    bag_idx += 1
                if grade_idx < len(reject_grades):
                    row["Grade"] = reject_grades[grade_idx]
                    grade_idx += 1
            else:
                if pal_idx < len(pal_counts):
                    row["SSCC Qty"] = f"{pal_counts[pal_idx]} PAL"
                    pal_idx += 1

            rows.append([row.get(c, "") for c in EXPECTED_COLUMNS])
    else:
        if debug:
            print(f"[WARN] {pdf_path.name}: No batches found.")
        rows.append([fields.get(c, "") for c in EXPECTED_COLUMNS])

    df = pd.DataFrame(rows, columns=EXPECTED_COLUMNS)
    return df.drop_duplicates().reset_index(drop=True)

def run(
    *,
    input_pdf: str,
    out: str,
    use_ocr: bool = False,
    debug: bool = False,
    generate_qc: bool = False,
) -> None:
    df = parse_export_pdf(input_pdf, use_ocr=use_ocr, debug=debug)
    df.to_csv(out, index=False)

    if generate_qc:
        from ..qc import validate, write_report
        
        # Run validation
        results = [validate(df, Path(input_pdf).name)]
        
        # Determine report path (same dir as output csv)
        out_path = Path(out)
        report_path = out_path.parent / "qc_report.md"
        
        write_report(results, report_path)
        if debug:
            print(f"[QC] Report written to {report_path}")

def run_batch(
    input_dir: Path,
    output_dir: Path,
    *,
    use_ocr: bool = False,
    debug: bool = False,
) -> None:
    """
    Batch-process all export PDFs in `input_dir` and write a single combined CSV
    to `output_dir/export_combined.csv`.
    """
    out_file = output_dir / "export_combined.csv"

    pdf_files = sorted(input_dir.glob("*.pdf"))
    print(f"[EXPORT] Found {len(pdf_files)} PDFs in {input_dir}")

    all_dfs: list[pd.DataFrame] = []
    for pdf in pdf_files:
        try:
            df = parse_export_pdf(str(pdf), use_ocr=use_ocr, debug=debug)
            df["Source_File"] = pdf.name
            all_dfs.append(df)
        except Exception as e:
            print(f"[EXPORT] ERROR processing {pdf.name}: {e}")

    if not all_dfs:
        print("[EXPORT] No data collected.")
        return

    combined = pd.concat(all_dfs, ignore_index=True)
    combined.to_csv(out_file, index=False)
    print(f"[EXPORT] Wrote combined CSV: {out_file}")
