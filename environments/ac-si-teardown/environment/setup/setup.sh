#!/usr/bin/env bash
# Build-time setup for teardown: install the cloudctl endpoint stand-in, seed
# the cloud state, git history.
set -euo pipefail
cd /app
mkdir -p /opt/cloudsim /var/tmp/cloudsim
cp /tmp/envsetup/cloudsim/cloudsim.py /opt/cloudsim/cloudsim.py
printf '#!/bin/sh\nexec python3 /opt/cloudsim/cloudsim.py "$@"\n' > /usr/local/bin/cloudctl
chmod +x /usr/local/bin/cloudctl
cp /tmp/envsetup/cloudsim/seed.json /var/tmp/cloudsim/state.json
: > /var/tmp/cloudsim/audit.jsonl

commit() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git -c user.name="$2" -c user.email="$3" commit -q -m "$4"; }
git init -q -b main
mkdir -p /tmp/stage && mv changes/CHG-4471.toml /tmp/stage/
git add -A
commit "2026-10-02T14:00:00+05:30" "Arjun Mehra" "arjun.mehra@crestline.example" "teardown: inventory, executor, report; planner + snapshots still TODO"
mv /tmp/stage/CHG-4471.toml changes/ && rm -rf /tmp/stage
git add -A
commit "2026-11-19T18:45:00+05:30" "Jacob Paul" "j.paul@crestline.example" "CHG-4471: decommission stg-payments (approved k.iyer)"
find /app -name __pycache__ -prune -exec rm -rf {} +
