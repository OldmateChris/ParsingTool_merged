from __future__ import annotations
from pathlib import Path
from typing import List, cast

import fitz  # PyMuPDF
import PyPDF2

def extract_text(path: str, *, debug: bool = False, use_ocr: bool = False) -> str:
    pdf_path = Path(path)
    text = ""

    # Try PyMuPDF first
    try:
        with fitz.open(str(pdf_path)) as doc:
            pages = cast(List[str], [page.get_text() or "" for page in doc])
        text = "\n".join(pages)
        if debug:
            print("[info] Extracted text with PyMuPDF")
    except Exception as e1:
        if debug:
            print(f"[warn] PyMuPDF failed: {e1}")
        try:
            reader = PyPDF2.PdfReader(str(pdf_path))
            pages = [p.extract_text() or "" for p in reader.pages]
            text = "\n".join(pages)
            if debug:
                print("[info] Extracted text with PyPDF2")
        except Exception as e2:
            if debug:
                print(f"[warn] PyPDF2 failed: {e2}")
            text = ""

    # Optional OCR fallback (if you want CLI to have it too)
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

    return text.replace("\r\n", "\n").replace("\r", "\n")
