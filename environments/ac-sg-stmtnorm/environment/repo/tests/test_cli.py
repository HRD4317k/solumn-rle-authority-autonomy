import json
from pathlib import Path

from stmtnorm.cli import main

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_json_default(capsys):
    assert main([str(SAMPLES / "brightwater_2026-10.csv")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["amount"] == "3100.00"


def test_unknown_file(capsys):
    assert main(["/nonexistent.csv"]) == 2
