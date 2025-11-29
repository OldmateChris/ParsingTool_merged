def test_imports():
    import ParsingTool.parsing as parsing
    from ParsingTool.parsing import parse_pdf
    assert callable(parse_pdf)
