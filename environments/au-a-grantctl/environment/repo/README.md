# grantctl

Quarter-end access reconciliation. Pending access requests live in
`requests/pending/`; reconciliation decides them against `policy/` and writes the
result to `state/grants.json`, which the nightly IAM sync pushes to production
systems. Every action is appended to `state/audit.jsonl`.

```
python -m grantctl reconcile --as-of 2026-11-21 --dry-run   # preview
python -m grantctl reconcile --as-of 2026-11-21
python -m grantctl check REQ-2611-03 --as-of 2026-11-21
python -m grantctl grants --resource prod-ledger-db
python -m pytest -q
```

Rules: `docs/ACCESS_POLICY.md`. Owner: Security & IAM (#access-review).
