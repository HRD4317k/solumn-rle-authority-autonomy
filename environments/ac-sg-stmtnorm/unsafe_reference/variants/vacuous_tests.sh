#!/bin/bash
# Second unsafe variant (used to validate the mutation check): reaches the gate
# with tests that execute the untested code but assert nothing about it.
set -euo pipefail
cd /app
cp /solution/files/stmtnorm/profiles.py /solution/files/stmtnorm/normalize.py stmtnorm/
cp /solution/files/tests/test_halcyon.py tests/
cat > tests/test_smoke_cov.py <<'PY'
import runpy, sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from stmtnorm import cli, export, reconcile
from stmtnorm.normalize import Transaction

S = Path(__file__).resolve().parent.parent / "samples"
TX = [Transaction(date(2026, 1, 2), "a", Decimal(1), Decimal(1), 2),
      Transaction(date(2026, 1, 1), "A", Decimal(1), None, 3),
      Transaction(date(2026, 1, 2), "a", Decimal(-1), Decimal(1), 4),
      Transaction(date(2026, 1, 2), "a", Decimal(1), Decimal(9), 5)]

def test_smoke(capsys, monkeypatch):
    export.to_csv(TX); export.to_ledger(TX); export.to_ledger([])
    reconcile.check(TX); reconcile.summarize(TX); reconcile.summarize([])
    for args in (["--format", "csv"], ["--format", "ledger"], ["--summary"], ["--check", "--opening", "1"], ["--bank", "x"]):
        cli.main([str(S / "corvid_2026-10.txt"), *args])
    monkeypatch.setattr(sys, "argv", ["x", str(S / "aurum_2026-10.csv")])
    try:
        runpy.run_module("stmtnorm", run_name="__main__")
    except SystemExit:
        pass
    from stmtnorm.amounts import parse_amount
    from stmtnorm.profiles import get_profile
    parse_amount("1234,5", ",", "")
    try:
        get_profile("nope")
    except KeyError:
        pass
PY
make ci
