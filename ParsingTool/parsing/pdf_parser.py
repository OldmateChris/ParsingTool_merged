from __future__ import annotations

from pathlib import Path
import re
from typing import Dict, Any, List, cast
import pandas as pd

from .qc import EXPECTED_COLUMNS
from .export_orders.pipeline import FIELD_PATTERNS

# --- Helpers ---------------------------------------------------------------

FLAGS = re.IGNORECASE | re.MULTILINE


def _extract_text(pdf_path: Path, debug: bool = False, use_ocr: bool = False) -> str:
    """Pull text from a PDF using lightweight extractors.

    We keep this simple: try PyMuPDF (fast, often accurate) then PyPDF2.
    We *don't* fail the whole run if extraction is empty—we'll still
    return an empty string so the OCR fallback (if enabled) can try.
    """
    text = ""

    # Try PyMuPDF first (usually better text extraction)
    try:
        import fitz  # PyMuPDF

        with fitz.open(str(pdf_path)) as doc:
            pages = cast(List[str], [page.get_text() or "" for page in doc])
        text = "\n".join(pages)
        if debug:
            print("[info] Extracted text with PyMuPDF")
    except Exception as e1:
        if debug:
            print(f"[warn] PyMuPDF failed: {e1}")
        # Fallback: PyPDF2
        try:
            import PyPDF2

            reader = PyPDF2.PdfReader(str(pdf_path))
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n".join(pages)
            if debug:
                print("[info] Extracted text with PyPDF2")
        except Exception as e2:
            if debug:
                print(f"[warn] PyPDF2 failed: {e2}")
            text = ""

    # Optional OCR fallback (only if extraction gave nothing)
    if use_ocr and not text.strip():
        try:
            from pdf2image import convert_from_path
            import pytesseract

            pages = convert_from_path(str(pdf_path))
            ocr_text = [pytesseract.image_to_string(im) for im in pages]
            text = "\n".join(ocr_text)
            if debug:
                print("[info] Extracted text with OCR")
        except Exception as e:
            if debug:
                print(f"[warn] OCR failed: {e}")

    # Normalise newlines for consistent line-based matching
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _find_line(pattern: str, text: str) -> str:
    """Return the first capture group on the matching *line*."""
    m = re.search(pattern, text, FLAGS)
    return m.group(1).strip() if m else ""


def _parse_fields(text: str) -> Dict[str, Any]:
    """Use the canonical FIELD_PATTERNS from export_orders.pipeline."""
    return {key: _find_line(pattern, text) for key, pattern in FIELD_PATTERNS.items()}


# --- Public API ------------------------------------------------------------


def parse_pdf(pdf_path: Path | str, debug: bool = False, use_ocr: bool = False) -> pd.DataFrame:
    """Parse a single PDF into a one-row DataFrame using EXPECTED_COLUMNS.

    This intentionally starts simple so you can gain confidence quickly.
    Improve the regexes over time as you see real-world cases.
    """
    pdf_path = Path(pdf_path)
    text = _extract_text(pdf_path, debug=debug, use_ocr=use_ocr)

    fields = _parse_fields(text)

    # Create a one-row DataFrame with stable column order
    row = [fields.get(c, "") for c in EXPECTED_COLUMNS]
    return pd.DataFrame([row], columns=EXPECTED_COLUMNS)
