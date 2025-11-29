from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict

import pandas as pd

from .qc import EXPECTED_COLUMNS
from .shared.pdf_utils import extract_text
from .shared.export_patterns import EXPORT_FIELD_PATTERNS

# Backwards-compat alias: other modules may still refer to FIELD_PATTERNS
FIELD_PATTERNS = EXPORT_FIELD_PATTERNS

# --- Helpers ---------------------------------------------------------------

FLAGS = re.IGNORECASE | re.MULTILINE


def _find_line(pattern: str, text: str) -> str:
    """Return the first capture group on the matching *line*.

    The pattern is expected to have exactly one capturing group which
    represents the value we want to extract from the line.
    """
    match = re.search(pattern, text, FLAGS)
    return match.group(1).strip() if match else ""


def _parse_fields(text: str) -> Dict[str, Any]:
    """Apply FIELD_PATTERNS to the text and return a dict of field -> value."""
    return {key: _find_line(pattern, text) for key, pattern in FIELD_PATTERNS.items()}


def _extract_text_compat(path: str, debug: bool, use_ocr: bool) -> str:
    """Call `extract_text` but stay compatible with simple monkeypatched fakes.

    In tests or older code, `extract_text` may be replaced with a function that
    accepts only a single positional argument (the path) and no keyword
    arguments. In that case, calling it with `debug=` would raise a TypeError.

    This helper tries the modern signature first, and if that fails due to a
    TypeError, falls back to calling the extractor with just the path.
    """
    try:
        return extract_text(path, debug=debug, use_ocr=use_ocr)
    except TypeError:
        # Likely a simple fake/monkeypatch that only takes `path`.
        return extract_text(path)


# --- Public API ------------------------------------------------------------


def parse_pdf(
    pdf_path: Path | str,
    debug: bool = False,
    use_ocr: bool = False,
) -> pd.DataFrame:
    """Parse a single PDF into a one-row DataFrame using EXPECTED_COLUMNS.

    Steps:
    1. Extract text from the PDF using the shared `extract_text` helper.
    2. Apply FIELD_PATTERNS to pull out individual fields.
    3. Build a one-row DataFrame with a stable column order defined by
       EXPECTED_COLUMNS.

    This intentionally stays simple so you can gain confidence quickly.
    You can improve the regex patterns over time as you see real-world
    documents that do not quite match.
    """
    pdf_path = Path(pdf_path)

    # Use a small compatibility wrapper so tests that monkeypatch
    # `extract_text` with a simple function still succeed.
    text = _extract_text_compat(str(pdf_path), debug=debug, use_ocr=use_ocr)

    # Turn the raw text into a dict of field -> value.
    fields = _parse_fields(text)

    # Create a one-row DataFrame with a stable column order.
    row = [fields.get(column, "") for column in EXPECTED_COLUMNS]
    return pd.DataFrame([row], columns=EXPECTED_COLUMNS)
