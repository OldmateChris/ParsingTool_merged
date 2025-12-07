from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

BASE_TEST_DIR = Path("pdf_csv_test_folders")


@dataclass
class ModeConfig:
    help: str
    input_subdir: str
    run_batch: Callable[[Path, Path, bool, bool], None]


# --- Thin wrappers that lazy-import the real pipeline code ---


def _run_export(input_dir: Path, output_dir: Path, use_ocr: bool, debug: bool) -> None:
    from ParsingTool.parsing.export_orders.pipeline import run_batch as export_run_batch

    export_run_batch(input_dir, output_dir, use_ocr=use_ocr, debug=debug)


def _run_domestic(input_dir: Path, output_dir: Path, use_ocr: bool, debug: bool) -> None:
    from ParsingTool.parsing.domestic_zapi.pipeline import run_batch as domestic_run_batch

    domestic_run_batch(input_dir, output_dir, use_ocr=use_ocr, debug=debug)


def _run_pi(input_dir: Path, output_dir: Path, use_ocr: bool, debug: bool) -> None:
    from ParsingTool.parsing.packing_list.pipeline import run_batch as pi_run_batch

    pi_run_batch(input_dir, output_dir, use_ocr=use_ocr, debug=debug)


MODES: dict[str, ModeConfig] = {
    "export": ModeConfig(
        help="Process export PDFs",
        input_subdir="input_export",
        run_batch=_run_export,
    ),
    "domestic": ModeConfig(
        help="Process domestic PDFs (batches + SSCC)",
        input_subdir="input_domestic",
        run_batch=_run_domestic,
    ),
    "pi": ModeConfig(
        help="Process PI / packing list PDFs",
        input_subdir="input_pi",
        run_batch=_run_pi,
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch runner for all pipelines")
    parser.add_argument("mode", choices=sorted(MODES.keys()))
    parser.add_argument("--ocr", action="store_true", help="Enable OCR fallback")
    parser.add_argument("--debug", action="store_true", help="Verbose debug logging")
    args = parser.parse_args()

    mode_cfg = MODES[args.mode]

    input_dir = BASE_TEST_DIR / mode_cfg.input_subdir
    output_dir = BASE_TEST_DIR / "output"

    print(f"[{args.mode.upper()}] Input: {input_dir}")
    print(f"[{args.mode.upper()}] Output dir: {output_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    mode_cfg.run_batch(input_dir, output_dir, args.ocr, args.debug)


if __name__ == "__main__":
    main()
