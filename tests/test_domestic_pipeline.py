# tests/test_domestic_pipeline.py
from ParsingTool.parsing.domestic_zapi import pipeline as dom

def test_domestic_pipeline_happy_path(tmp_path, monkeypatch):
    SAMPLE_TEXT = """
    Delivery 123456
    Picking request 987654
    Customer: FUTURE FRUIT CO
    Customer delivery date: 10/02/2025
    Date requested: 09/02/2025
    Requested by: Alice QA

    Batch Number: F013561001
    OLAM Ref: OL-777
    SSCC Qty: 2
    Product: Variety: Gala   Grade: A1   Size: 100-110   Packaging: Box
    SSCC: 003123456789012345
    SSCC: 003123456789012346
    """

    def fake_extract_text(_path: str) -> str:
        return SAMPLE_TEXT

    monkeypatch.setattr(dom, "extract_text", fake_extract_text)

    out_batches = tmp_path / "batches.csv"
    out_sscc = tmp_path / "sscc.csv"

    dom.run(input_pdf="dummy.pdf", out_batches=str(out_batches), out_sscc=str(out_sscc))

    assert out_batches.exists()
    assert out_sscc.exists()

    batches = out_batches.read_text(encoding="utf-8").splitlines()
    sscc = out_sscc.read_text(encoding="utf-8").splitlines()

    assert "Batch Number" in batches[0]
    assert "SSCC" in sscc[0]
    assert any("F013561001" in line for line in batches[1:])
    assert any("003123456789012345" in line for line in sscc[1:])
