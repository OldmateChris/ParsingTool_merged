import os, subprocess, sys

ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

def test_cli_top_level_help():
    r = subprocess.run([sys.executable, "-m", "ParsingTool.parsing.cli", "--help"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0
    assert "parsing tool cli" in r.stdout.lower()

def test_cli_domestic_help():
    r = subprocess.run([sys.executable, "-m", "ParsingTool.parsing.cli", "domestic", "--help"],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0
    assert "domestic" in r.stdout.lower()
