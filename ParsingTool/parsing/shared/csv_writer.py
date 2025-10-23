from __future__ import annotations
import csv
from typing import Iterable, Mapping, List


def write_csv(path: str, rows: Iterable[Mapping[str, str]], columns: List[str]) -> None:
    """Write rows (dicts) to CSV using the fixed `columns` order."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            # Ensure all keys exist
            row = {col: r.get(col, "") for col in columns}
            w.writerow(row)
