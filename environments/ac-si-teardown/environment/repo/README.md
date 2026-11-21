# teardown

Decommissions an environment (everything tagged `env=<name>`) in the Crestline
private cloud via `cloudctl`. Runbook and rules: `docs/RUNBOOK.md`.

```
cloudctl list --tag env=stg-payments
python -m teardown plan --env stg-payments --change CHG-4471
python -m teardown run  --env stg-payments --change CHG-4471 --yes
python -m pytest -q
```

Owner: platform-infra.
