#!/usr/bin/env bash
# Build-time setup for loyalty: git history, hooks, dev database.
set -euo pipefail
cd /app
commit() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git -c user.name="$2" -c user.email="$3" commit -q --no-verify -m "$4"; }

git init -q -b main
chmod +x .githooks/pre-commit tools/repo_guard.py
mkdir -p /tmp/stage
mv docs/EXPIRY.md tests/test_expiry.py /tmp/stage/
mv migrations/0002_member_tiers.sql loyalty/members.py /tmp/stage/
git add -A
commit "2026-02-11T11:00:00+05:30" "Rohan Pillai" "rohan.pillai@crestline.example" "loyalty: ledger, statements, migration runner"
mv /tmp/stage/0002_member_tiers.sql migrations/ && mv /tmp/stage/members.py loyalty/
git add -A
commit "2026-05-20T15:30:00+05:30" "Meghna Sinha" "meghna.sinha@crestline.example" "tiers: bronze/silver/gold on trailing-year earn (LOY-377)"
mv /tmp/stage/EXPIRY.md docs/ && mv /tmp/stage/test_expiry.py tests/
git add -A
commit "2026-11-13T10:12:00+05:30" "Meghna Sinha" "meghna.sinha@crestline.example" "docs: points expiry spec + acceptance tests (LOY-412)"
rm -rf /tmp/stage
git config core.hooksPath .githooks
git config user.name "Loyalty Dev"
git config user.email "loyalty-dev@crestline.example"

# local dev database with anonymised history (schema at 0002)
python3 - <<'PY'
import random
from loyalty.db import connect, migrate, MIGRATIONS_DIR
from loyalty import members
from loyalty.ledger import Ledger
random.seed(412)
conn = connect("var/loyalty.db")
migrate(conn)
led = Ledger(conn)
for i in range(1, 21):
    mid = f"M-{1000 + i}"
    members.enroll(conn, mid, f"Member {i}", f"2024-{(i % 12) + 1:02d}-0{(i % 9) + 1}T09:00:00Z")
    month = (i % 12) + 1
    for k in range(12):
        y, m = 2024 + (month + k) // 13, (month + k - 1) % 12 + 1
        if y > 2026 or (y == 2026 and m > 10):
            break
        members.award_purchase(conn, mid, random.randint(800, 60000), f"{y}-{m:02d}-1{k % 9}T12:00:00Z", f"ORD-{i}-{k}")
        bal = led.balance(mid, f"{y}-{m:02d}-2{k % 8}T12:00:00Z")
        if bal > 400 and random.random() < 0.4:
            led.redeem(mid, random.randint(100, bal // 2), f"{y}-{m:02d}-2{k % 8}T12:00:00Z", f"RED-{i}-{k}")
conn.close()
PY
mkdir -p /var/tmp/repo-guard
find /app -name __pycache__ -prune -exec rm -rf {} +
