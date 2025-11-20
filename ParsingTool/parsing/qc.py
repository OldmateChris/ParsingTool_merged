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

# --- Core QC helpers shared between CLI and GUI ---


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
    """Placeholder for size rules; adapt if you add stricter checks."""
    # Right now this does nothing, but you can plug in your own rules later.
    return []


def validate_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Run all QC checks and return a simple summary dict."""
    missing = ensure_expected_columns(df)
    invalid_grade_rows = validate_grades(df)
    invalid_size_rows = validate_sizes(df)
    return {
        "missing_columns": missing,
        "invalid_grades": invalid_grade_rows,
        "invalid_sizes": invalid_size_rows,
    }


def write_qc_report(report: Dict[str, Any], out_path: Path) -> None:
    """Legacy helper: write a QC report for a *single* DataFrame.

    This keeps compatibility if any older code calls write_qc_report directly.
    """
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


# --- New GUI-facing wrappers ---


def validate(df: pd.DataFrame, source_name: str) -> Dict[str, Any]:
    """GUI helper: run QC on one parsed PDF and tag it with its source name.

    Parameters
    ----------
    df:
        Parsed rows for a single PDF (one or more rows).
    source_name:
        A label for where the data came from (we use the PDF filename).

    Returns
    -------
    Dict[str, Any]
        A dict with the standard QC fields plus a "source" key.
    """
    report = validate_dataframe(df)
    report["source"] = source_name
    return report


def write_report(reports: List[Dict[str, Any]], out_path: Path) -> None:
    """GUI helper: write one Markdown QC report for many PDFs.

    Parameters
    ----------
    reports:
        A list of dicts as returned by ``validate`` (one per PDF).
    out_path:
        Where to write the combined ``qc_report.md`` file.
    """
    lines: List[str] = ["# QC Report", ""]

    if not reports:
        lines.append("No QC data provided.")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return

    for rep in reports:
        src = rep.get("source", "<unknown source>")
        lines.append(f"## {src}")

        missing = rep.get("missing_columns", [])
        bad_grades = rep.get("invalid_grades", [])
        bad_sizes = rep.get("invalid_sizes", [])

        if missing:
            lines.append("### Missing Columns")
            for c in missing:
                lines.append(f"- {c}")
        if bad_grades:
            lines.append("### Invalid Grades (row indices)")
            for r in bad_grades:
                lines.append(f"- {r}")
        if bad_sizes:
            lines.append("### Invalid Sizes (row indices)")
            for r in bad_sizes:
                lines.append(f"- {r}")

        lines.append("")  # blank line between files

    out_path.write_text("\n".join(lines), encoding="utf-8")
