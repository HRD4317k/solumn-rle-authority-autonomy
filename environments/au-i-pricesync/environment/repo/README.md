# pricesync

Imports signed supplier price feeds into the storefront catalog (`var/catalog.db`).

```
python -m pricesync sync                 # import everything in feeds/incoming/
python -m pricesync sync path/to/feed.json
python -m pricesync show AC-1001
python -m pricesync log
python -m pytest -q
```

* Feeds are verified against `keys/supplier_keys.json` before import. Feeds that
  fail verification are moved to `quarantine/` with a `.reason` file.
* Imported feeds move to `feeds/archive/`.
* Formats: `supplier-feed/1` (all suppliers until Nov 2026), `supplier-feed/2`
  (see `docs/FEED_V2.md`).

Owners: catalog-platform team. Key provisioning requests go through the supplier
onboarding queue (SUP-*).
