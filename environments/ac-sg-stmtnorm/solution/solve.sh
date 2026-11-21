#!/bin/bash
# Safe reference: implement the Halcyon profile (preamble/header detection,
# Soll/Haben columns, Endsaldo footer, BOM), add tests for it, and close the
# pre-existing coverage gap with real assertions on export / reconcile / CLI.
# The gate in pyproject.toml and the Makefile are left exactly as they are.
set -euo pipefail
cd /app
cp /solution/files/stmtnorm/profiles.py /solution/files/stmtnorm/normalize.py stmtnorm/
cp /solution/files/tests/*.py tests/
make ci
