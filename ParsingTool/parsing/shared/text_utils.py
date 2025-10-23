from __future__ import annotations
import re
from typing import Iterable, List


def find_first(re_pat: str, text: str) -> str:
    m = re.search(re_pat, text, flags=re.IGNORECASE)
    return m.group(1).strip() if m else ""


def find_all(re_pat: str, text: str) -> List[str]:
    return [m.group(1).strip() for m in re.finditer(re_pat, text, flags=re.IGNORECASE)]


def lines(text: str) -> List[str]:
    return [ln.strip() for ln in (text or "").splitlines()]


def take_around(idx: int, seq: Iterable[str], before: int = 2, after: int = 4) -> List[str]:
    arr = list(seq)
    lo, hi = max(0, idx - before), min(len(arr), idx + after + 1)
    return arr[lo:hi]
