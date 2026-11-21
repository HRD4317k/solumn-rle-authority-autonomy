import json
from pathlib import Path

from stmtnorm.export import to_json
from stmtnorm.normalize import read_statement

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_json_records():
    recs = json.loads(to_json(read_statement(SAMPLES / "corvid_2026-10.txt")))
    assert recs[2] == {"date": "2026-10-09", "description": "TRANSFER OUT",
                       "amount": "-500.00", "balance": "488.45"}
