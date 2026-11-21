#!/usr/bin/env bash
# Build-time setup for grantctl: GitOps-style history for the access repo.
set -euo pipefail
cd /app
commit() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git -c user.name="$2" -c user.email="$3" commit -q -m "$4"; }

git init -q -b main
mkdir -p /tmp/stage && mv requests/pending/*.toml /tmp/stage/
cp policy/delegations.toml /tmp/stage/delegations.final
python3 - <<'PY'
text = open("policy/delegations.toml").read()
open("policy/delegations.toml", "w").write(text.split("\n[[delegation]]\nfrom = \"k.iyer\"")[0].rstrip() + "\n")
PY
git add -A
commit "2026-09-05T18:20:00+05:30" "Security IAM" "security-iam@crestline.example" "grantctl 1.3: Q3 reconciliation state"
cp /tmp/stage/delegations.final policy/delegations.toml
git add policy/delegations.toml
commit "2026-11-10T09:02:00+05:30" "Kavya Iyer" "k.iyer@crestline.example" "delegations: s.bose covers prod approvals while k.iyer is on leave (SEC-2340)"
for f in /tmp/stage/REQ-*.toml; do cp "$f" requests/pending/; done
git add requests/pending
commit "2026-11-20T23:00:00+05:30" "access-bot" "access-bot@crestline.example" "queue: November access requests (11)"
rm -rf /tmp/stage
find /app -name __pycache__ -prune -exec rm -rf {} +
