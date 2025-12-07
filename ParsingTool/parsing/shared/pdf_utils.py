from __future__ import annotations
from pathlib import Path
from typing import List, cast

import fitz  # PyMuPDF
import PyPDF2

class NoTextError(RuntimeError):
    """Raised when we can't get any usable text from a PDF."""
    pass

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
    
    # If we got only a tiny amount of text, treat it as image-only
    # and run OCR when the user has enabled it.
    MIN_TEXT_CHARS_FOR_NO_OCR = 200

    if use_ocr and len(text.strip()) < MIN_TEXT_CHARS_FOR_NO_OCR:
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

    # Normalise line endings
    clean = text.replace("\r\n", "\n").replace("\r", "\n")

    # If we still have no text, signal that this file basically
    # needs OCR (image-only or corrupted).
    if not clean.strip():
        if debug:
            print("[warn] No extractable text found in PDF")
        if not use_ocr:
            # Only raise this special error when OCR is disabled;
            # with OCR enabled it's just a hard failure.
            raise NoTextError(f"No extractable text in {pdf_path.name}")

    return clean

