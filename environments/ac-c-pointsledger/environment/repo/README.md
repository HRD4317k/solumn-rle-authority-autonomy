# loyalty

Points ledger for the Crestline rewards programme.

```
python -m loyalty --db var/loyalty.db migrate
python -m loyalty --db var/loyalty.db balance M-1001
python -m loyalty --db var/loyalty.db statement M-1001 2026-10
python -m pytest -q
```

`var/loyalty.db` is a local dev database with anonymised sample members.
