from ParsingTool.parsing.shared.schemas import BATCHES_COLUMNS, SSCC_COLUMNS

def test_batches_has_expected_columns():
    assert "Batch Number" in BATCHES_COLUMNS
    assert "Delivery Number" in BATCHES_COLUMNS

def test_sscc_has_expected_columns():
    assert "SSCC" in SSCC_COLUMNS
    assert "Batch Number" in SSCC_COLUMNS
