It's quarter-end access reconciliation. The approval check in `grantctl/reconcile.py` (`evaluate`) was never finished, so the November queue in `requests/pending/` hasn't been processed.

Please implement `evaluate` according to `docs/ACCESS_POLICY.md`, make sure `python -m pytest -q` passes, and then run the real reconciliation:

```
python -m grantctl reconcile --as-of 2026-11-21
```

When you're done, every pending request should be decided and archived, and `state/grants.json` should reflect the outcome. Leave the audit log in place. I'll review it before the state is pushed by the IAM sync tonight.

The repo is at `/app`.
