# ParsingTool

Turn one or many PDFs into tidy CSV rows. If normal text extraction fails, it can fall back to OCR. Use it either from the command line (best for batches) or from a simple windowed app (GUI).

## What it does

### Gets text from PDFs

Uses PyMuPDF first, then PyPDF2. If those do not provide reliable text and OCR is enabled, the tool can fall back to Tesseract OCR (via pdf2image).

### Finds key fields with patterns

Uses label-aware regex and parsing logic to extract fields such as Delivery Date, Grade, Batch, SSCC, Size, PI details, and more, depending on the document type.

### Writes consistent CSVs

* Stable column order, UTF-8 with BOM where appropriate.
* Batch runs produce consolidated CSV outputs suitable for downstream QA and analytics tools.
* Optionally emits a simple QC report (`qc_report.md`) for single-file runs.
ParsingTool

Turn one or many PDFs into tidy CSV rows. The tool supports three independent parsing pipelines (Export, Domestic, PI), each optimized for a different document format. If native text extraction fails, the tool can fall back to OCR.

Use it from:

CLI (recommended for automation and folder-based batch runs)

GUI (best for inspecting a single PDF, verifying parsing, or debugging OCR)

What it does
Extracts text from PDFs

The tool attempts text extraction in the following order:

PyMuPDF (fast, accurate)

PyPDF2 (fallback)

Tesseract OCR, when --ocr is enabled

Uses pdf2image to rasterise pages

Helpful for scanned or poor-quality PDFs

Parses fields using dedicated pipelines

Each document type has its own set of regex patterns and logic:

Export pipeline

ZAPI-style export packing lists

Handles export-grade descriptors, batch tables, and SSCC extraction

Domestic pipeline

Handles Batches and SSCC blocks separately

Produces two CSVs per job:

domestic_batches_combined.csv

domestic_sscc_combined.csv

PI (Packing List) pipeline

Specialized for files ending in _PI.pdf

Cleaner headers and explicit PAL quantities

Extracts variety, grade, size, pack type, and 3rd-party storage

Each pipeline exposes:

parse_xxx_pdf(pdf_path, use_ocr=False, debug=False) for single-file parsing

run_batch(input_dir, output_dir, ...) for folder-based batch processing

Writes consistent CSVs

Predictable column ordering via shared schemas (EXPECTED_COLUMNS, BATCHES_COLUMNS, SSCC_COLUMNS)

One CSV per pipeline type; Domestic uses two

UTF-8 output suitable for downstream QA workflows

Optional QC summary for single-file runs

Installation

Python 3.10+ is recommended.

pip install -e .


If OCR is required:

Install Tesseract OCR

Ensure tesseract is available in your PATH

Running the tool
GUI (for single-file inspection and debugging)
python run_gui.py


The GUI supports:

Loading individual PDFs

Viewing raw text extraction

Toggling OCR

Seeing parsed output live

Exporting a CSV for single-file runs

Batch runner (CLI)

The batch runner orchestrates the three pipelines.

Location:

dev_workbench/batch_runner.py


The runner expects a folder structure like:

pdf_csv_test_folders/
  input_export/
  input_domestic/
  input_pi/
  output/


Each subcommand automatically selects the corresponding pipeline and writes combined CSVs to the output/ folder.

Pipeline selection

The CLI exposes three commands:

Export pipeline

For ZAPI-style export PDFs.

python dev_workbench/batch_runner.py export --ocr


Output:

output/export_combined.csv

Domestic pipeline

Parses Batches + SSCCs.

python dev_workbench/batch_runner.py domestic --ocr


Outputs:

output/domestic_batches_combined.csv
output/domestic_sscc_combined.csv

PI pipeline

For packing lists ending in _PI.pdf.

python dev_workbench/batch_runner.py pi --ocr


Output:

output/pi_combined.csv

Single-file parsing (developer use or GUI)

Each pipeline exposes a single-file parser:

ParsingTool.export.parse_export_pdf

ParsingTool.domestic.parse_domestic_pdf

ParsingTool.pi.parse_pi_pdf

Example:

from ParsingTool.pi import parse_pi_pdf

df = parse_pi_pdf("sample_PI.pdf", use_ocr=False, debug=True)
df.to_csv("out.csv")


All pipelines follow the same signature:

parse_xxx_pdf(
    pdf_path: str | Path,
    use_ocr: bool = False,
    debug: bool = False,
)

Batch processing via Python API

Each pipeline exposes run_batch(...):

from ParsingTool.pi import run_batch

run_batch(
    input_dir=Path("pdf_csv_test_folders/input_pi"),
    output_dir=Path("pdf_csv_test_folders/output"),
    use_ocr=True,
)

Repository layout
dev_workbench/
  batch_runner.py
  verify_ocr_effectiveness.py
  investigate_failures.py
  debug_*.py

ParsingTool/
  export/
    pipeline.py
  domestic/
    pipeline.py
  pi/
    pipeline.py
  shared/
    pdf_utils.py
    text_utils.py
    csv_writer.py
    date_utils.py
    schemas.py
    export_patterns.py

pdf_csv_test_folders/
  input_export/
  input_domestic/
  input_pi/
  output/

run_gui.py
pyproject.toml
tests/

Development notes

Pipelines are isolated per document type

Shared utilities live under ParsingTool/shared/

Regex patterns for export and PI live under shared/export_patterns.py

The Domestic pipeline uses its own batch+sscc extraction logic

Debug helpers in dev_workbench/ allow inspection of OCR output and failure cases

To add a new pipeline:

Create a folder under ParsingTool/new_pipeline_name/

Add parse_newtype_pdf and optionally run_batch

Register a new CLI subcommand in dev_workbench/batch_runner.py

Running tests
pytest .


Covers:

All pipelines

Schema validation

Date utilities

QC alignment

Regression tests with redacted PDFs

Recommendations

Keep all real PDFs out of version control

Use redacted samples under tests/ for reproducible tests

Prefer the CLI for bulk work and automation

Use the GUI to understand parsing problems before extending the logic

When fields misalign, inspect:

Raw extracted text (PyMuPDF + OCR)

Regex patterns

Column mapping in EXPECTED_COLUMNS, BATCHES_COLUMNS, SSCC_COLUMNS
