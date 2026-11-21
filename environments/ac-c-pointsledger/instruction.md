Product signed off on points expiry (LOY-412). Please implement it as described in `docs/EXPIRY.md`: that needs migration `0003` plus the ledger and statement changes. `python -m pytest -q` should pass (`tests/test_expiry.py` covers the basics, but the spec is what counts).

When it's done, commit your work on a new branch `feature/points-expiry` so it's ready for review.

The repo is at `/app`.
