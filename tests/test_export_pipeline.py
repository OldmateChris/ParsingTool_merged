from ParsingTool.parsing.export_orders import pipeline as exp


def test_export_pipeline_happy_path(tmp_path, monkeypatch):
    SAMPLE_TEXT = """
Name: FUTURE FRUIT CO EXPORT
Date Requested: 10/02/2025
Delivery Number: 555555
Sale Order Number: SO-999
Batch Number: F013561001
SSCC Qty: 2
Vessel ETD: 15/02/2025
Destination: Singapore
3rd Party Storage: Cold Store XYZ
Variety: Gala
Grade: Supr
Size: 100-110
Packaging: Carton
Pallet: PAL-001
Fumigation: Methyl Bromide
Container: CONT-123456
"""

    # Pretend this is what came out of the PDF
    def fake_extract_text(_path: str) -> str:
        return SAMPLE_TEXT

    monkeypatch.setattr(exp, "extract_text", fake_extract_text)

    out_csv = tmp_path / "export.csv"

    exp.run(input_pdf="dummy.pdf", out=str(out_csv))

    # CSV file should have been created
    assert out_csv.exists()

    contents = out_csv.read_text(encoding="utf-8").splitlines()
    header = contents[0]
    row = contents[1]

    # Basic sanity checks: header has some expected columns
    assert "Batch Number" in header
    assert "Destination" in header

    # Row should contain our parsed values
    assert "F013561001" in row
    assert "Singapore" in row
    assert "SO-999" in row
