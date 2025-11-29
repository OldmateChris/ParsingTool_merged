"""
Beginner-friendly API surface for the ParsingTool.

Usage:
    from ParsingTool.parsing import parse_pdf
"""
from .pdf_parser import parse_pdf  # re-export for convenience

__all__ = ["parse_pdf"]
