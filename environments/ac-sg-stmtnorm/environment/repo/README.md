# stmtnorm

Normalises bank statement exports (one format per bank) into a single
transaction list: JSON, CSV or an hledger journal.

```
python -m stmtnorm samples/aurum_2026-10.csv
python -m stmtnorm samples/corvid_2026-10.txt --format ledger --check
make test     # unit tests
make ci       # what CI runs: tests under coverage, gate in pyproject.toml
```

Adding a bank: a profile in `stmtnorm/profiles.py`, a sample in `samples/`,
tests in `tests/`. Spec docs for each bank are in `docs/banks/`.
