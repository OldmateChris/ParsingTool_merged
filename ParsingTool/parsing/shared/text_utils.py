from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Any

# Shared regex flags for all text matching in this module
FLAGS = re.IGNORECASE | re.MULTILINE


def find_first(re_pat: str, text: str) -> str:
    """Return the first capture group match for re_pat in text, or "" if none.

    Patterns are matched case-insensitively and in multiline mode so that
    ^ and $ work per line, not just on the whole string.
    """
    if not text:
        return ""
    m = re.search(re_pat, text, flags=FLAGS)
    if not m:
        return ""
    # Guard against patterns without a capturing group
    try:
        value = m.group(1)
    except IndexError:
        return ""
    return value.strip() if value is not None else ""


def find_all(re_pat: str, text: str) -> List[str]:
    """Return all first capture group matches for re_pat in text.

    Uses the same FLAGS (IGNORECASE | MULTILINE) so line-anchored
    patterns with ^ and $ work correctly.
    """
    if not text:
        return []
    values: List[str] = []
    for m in re.finditer(re_pat, text, flags=FLAGS):
        try:
            value = m.group(1)
        except IndexError:
            continue
        if value is not None:
            values.append(value.strip())
    return values


def lines(text: str) -> List[str]:
    r"""Split text into a list of lines, preserving order.

    Leading/trailing whitespace is left as-is so that regexes can
    decide what to trim using \s* where appropriate.
    """
    if not text:
        return []
    return text.splitlines()


def take_around(idx: int, seq: Sequence[Any], before: int = 2, after: int = 4) -> List[Any]:
    """Return a window of items around index idx from seq.

    Helpful when debugging parsing by looking at lines near a match.
    """
    if not seq:
        return []
    lo = max(0, idx - before)
    hi = min(len(seq), idx + after + 1)
    return list(seq[lo:hi])
