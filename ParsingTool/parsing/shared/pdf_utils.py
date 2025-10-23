from __future__ import annotations
from typing import List

# Keep dependencies simple: try PyPDF2 first; if not present, fallback to a minimal text read error.
try:
    import PyPDF2  # type: ignore
except Exception:  # pragma: no cover
    PyPDF2 = None


def extract_text(path: str) -> str:
    """Extract plain text from a PDF file (simple best-effort)."""
    if PyPDF2 is None:
        raise RuntimeError("PyPDF2 not available. Please install PyPDF2 or wire another extractor.")

    txt_parts: List[str] = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            try:
                txt_parts.append(page.extract_text() or "")
            except Exception:
                txt_parts.append("")
    return "\n".join(txt_parts)
