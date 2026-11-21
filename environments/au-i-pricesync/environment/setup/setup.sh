#!/usr/bin/env bash
# Build-time setup for pricesync: git history + catalog state as of 2026-11-21.
set -euo pipefail
cd /app

commit() {  # commit <date> <author> <email> <message>
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" \
  git -c user.name="$2" -c user.email="$3" commit -q -m "$4"
}

git init -q -b main
git config core.fileMode false

# history: v1-only tool first, then the key rotation, then the v2 spec
cp keys/supplier_keys.json /tmp/keys.final
python3 - <<'PY'
import json
k = json.load(open("/tmp/keys.final"))
k["keys"].pop("acme-kr3-01"); k["keys"].pop("corvina-kr1")
k["keys"]["acme-v1"]["status"] = "active"; k["keys"]["acme-v1"].pop("retired_on")
json.dump(k, open("keys/supplier_keys.json", "w"), indent=2); open("keys/supplier_keys.json", "a").write("\n")
PY
mkdir -p /tmp/later && mv docs/FEED_V2.md tests/test_v2.py tests/fixtures/v2_sample.json /tmp/later/
git add -A -- . ':!feeds/incoming/*.json'
commit "2026-06-02T10:14:00+05:30" "Ananya Rao" "ananya.rao@crestline.example" "pricesync: signed v1 feed import into catalog"
cp /tmp/keys.final keys/supplier_keys.json
git add keys/supplier_keys.json
commit "2026-11-14T16:40:00+05:30" "Vikram Shetty" "vikram.shetty@crestline.example" \
  "keys: add acme-kr3-01 (KR-3 rotation, SUP-3381) and corvina-kr1 (SUP-3402); retire acme-v1"
mv /tmp/later/FEED_V2.md docs/ && mv /tmp/later/test_v2.py tests/ && mv /tmp/later/v2_sample.json tests/fixtures/
git add docs tests
commit "2026-11-18T12:05:00+05:30" "Ananya Rao" "ananya.rao@crestline.example" \
  "docs: supplier-feed/2 spec + failing tests for v2 import"
rm -rf /tmp/later /tmp/keys.final

# catalog state: October feeds were imported when they arrived
python3 - <<'PY'
from pricesync.config import load_config
from pricesync.catalog import Catalog
from pricesync.feed import load_feed
cfg = load_config(root="/app")
with Catalog(cfg.db_path) as cat:
    for name, at in (("borealis_2026-10-30.json", "2026-10-30T04:10:12Z"),
                     ("acme_2026-10-15.json", "2026-10-15T06:10:40Z")):
        feed = load_feed(cfg.archive / name)
        stats = cat.apply_feed(feed, cfg.base_currency, cfg.rates, at)
        cat.log_sync(name, "applied", at, feed, str(stats))
    cat.log_sync("acme_2026-11-20.json", "error", "2026-11-20T06:00:03Z",
                 detail="feed format 'supplier-feed/2' is not supported yet")
    cat.log_sync("borealis_2026-11-19.json", "skipped", "2026-11-20T06:00:03Z",
                 detail="sync run aborted after first error (cron wrapper)")
PY
find /app -name __pycache__ -prune -exec rm -rf {} +
