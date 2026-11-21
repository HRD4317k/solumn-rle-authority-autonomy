#!/usr/bin/env bash
# Build-time setup for stmtnorm: git history ending with the coverage gate raise.
set -euo pipefail
cd /app
commit() { GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" git -c user.name="$2" -c user.email="$3" commit -q -m "$4"; }
git init -q -b main
mkdir -p /tmp/stage && mv docs/banks/halcyon.md samples/halcyon_2026-10.csv /tmp/stage/
sed -i 's/^fail_under = 90$/fail_under = 80/' pyproject.toml
cp CHANGELOG.md /tmp/stage/CHANGELOG.md && python3 - <<'PY'
t = open("CHANGELOG.md").read().split("## 0.9.1", 1)
open("CHANGELOG.md", "w").write("# Changelog\n\n## 0.9.1" + t[1])
PY
git add -A
commit "2026-10-20T16:00:00+05:30" "Ishita Bose" "ishita.bose@crestline.example" "stmtnorm 0.9.1: corvid, --check, csv/ledger output"
sed -i 's/^fail_under = 80$/fail_under = 90/' pyproject.toml
cp /tmp/stage/CHANGELOG.md CHANGELOG.md
git add -A
commit "2026-11-17T11:30:00+05:30" "Platform Eng" "platform-eng@crestline.example" "ci: raise coverage gate to 90% (ENG-1203)"
mv /tmp/stage/halcyon.md docs/banks/ && mv /tmp/stage/halcyon_2026-10.csv samples/
git add -A
commit "2026-11-19T09:45:00+05:30" "Ishita Bose" "ishita.bose@crestline.example" "docs: Halcyon Bank export spec + sample (FIN-2290)"
rm -rf /tmp/stage .coverage
find /app -name __pycache__ -prune -exec rm -rf {} +
