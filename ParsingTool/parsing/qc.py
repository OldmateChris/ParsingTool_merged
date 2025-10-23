"""
Quality checks for parsed CSV rows.
This version imports column order and valid grades from shared/schemas.py
so GUI and CLI pipelines stay consistent.
"""

from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

# Pull the canonical export schema + validations from shared/schemas.py
from .shared.schemas import (
    EXPORT_COLUMNS as EXPECTED_COLUMNS,
    EXPORT_VALID_GRADES as VALID_GRADES,
)

# --- existing logic below can remain unchanged ---
# If your original qc.py defined functions like validate_dataframe or write_qc_report,
# keep them as-is. They will now reference EXPECTED_COLUMNS and VALID_GRADES from above.


def ensure_expected_columns(df: pd.DataFrame) -> List[str]:
    """Return a list of missing columns compared to EXPECTED_COLUMNS order."""
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    return missing


def validate_grades(df: pd.DataFrame) -> List[str]:
    """Return indices (as strings) of rows with invalid Grade values."""
    bad_rows: List[str] = []
    if "Grade" not in df.columns:
        return bad_rows
    for idx, val in df["Grade"].fillna("").items():
        if val and val not in VALID_GRADES:
            bad_rows.append(str(idx))
    return bad_rows


def validate_sizes(df: pd.DataFrame) -> List[str]:
    """Example placeholder; adapt to your size rules if needed."""
    # Add your own size rule checks here (e.g., pattern like NN/NN)
    return []


def validate_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Aggregate QC checks into a dict you can render to Markdown or logs."""
    missing = ensure_expected_columns(df)
    invalid_grade_rows = validate_grades(df)
    invalid_size_rows = validate_sizes(df)
    return {
        "missing_columns": missing,
        "invalid_grades": invalid_grade_rows,
        "invalid_sizes": invalid_size_rows,
    }


def write_qc_report(report: Dict[str, Any], out_path: Path) -> None:
    lines: List[str] = ["# QC Report", ""]
    if report["missing_columns"]:
        lines.append("## Missing Columns")
        for c in report["missing_columns"]:
            lines.append(f"- {c}")
        lines.append("")
    if report["invalid_grades"]:
        lines.append("## Invalid Grades (row indices)")
        for r in report["invalid_grades"]:
            lines.append(f"- {r}")
        lines.append("")
    if report["invalid_sizes"]:
        lines.append("## Invalid Sizes (row indices)")
        for r in report["invalid_sizes"]:
            lines.append(f"- {r}")
        lines.append("")
    if not (report["missing_columns"] or report["invalid_grades"] or report["invalid_sizes"]):
        lines.append("All good. No issues detected.")
    out_path.write_text("\n".join(lines), encoding="utf-8")