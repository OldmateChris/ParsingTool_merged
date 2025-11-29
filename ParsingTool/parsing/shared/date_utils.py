from __future__ import annotations
import re

_DATE_RE = re.compile(r"\b(\d{2})[./-](\d{2})[./-](\d{4})\b")


def to_ddmmyyyy(text: str) -> str:
    """Find a date like 10.02.2025 or 10/02/2025 and return '10/02/2025'.
    Returns empty string if nothing matches.
    """
    m = _DATE_RE.search(text or "")
    if not m:
        return ""
    d, mth, y = m.group(1), m.group(2), m.group(3)
    return f"{d}/{mth}/{y}"
