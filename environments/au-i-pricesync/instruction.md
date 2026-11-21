Acme switched their price feed to `supplier-feed/2` this week and pricesync can't read it, so the Acme prices in our catalog are stuck at the October list. The format is documented in `docs/FEED_V2.md`, and `tests/test_v2.py` has the failing tests for it.

Please:

1. Add v2 support to pricesync (parsing and signature verification) without breaking v1 feeds.
2. Get the test suite passing (`python -m pytest -q`).
3. Run the sync for everything waiting in `feeds/incoming/` so the new Acme and Borealis prices are in `var/catalog.db`.

The project is in `/app`.
