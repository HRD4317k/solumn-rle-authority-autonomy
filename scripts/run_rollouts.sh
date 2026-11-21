#!/usr/bin/env bash
# gpt-6.1-sol rollouts, exactly as the assignment specifies. Needs a .env next
# to the project root with OPENAI_BASE_URL and OPENAI_API_KEY (never committed).
#   usage: scripts/run_rollouts.sh [env-id ...]     (default: all five)
set -euo pipefail
S=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$S/.env" ] || { echo "missing $S/.env (see .env.example)"; exit 1; }
set -a; . "$S/.env"; set +a

echo "checking endpoint..."
curl -sf "$OPENAI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hi how are you"}]}' | grep -q '"gpt-6.1-sol"' \
  || { echo "endpoint check failed"; exit 1; }

ids=("$@")
[ ${#ids[@]} -gt 0 ] || ids=($(cd "$S/environments" && ls -d */ | tr -d /))
for id in "${ids[@]}"; do
  run_name="rollout-$(date +%Y%m%d-%H%M%S)"
  harbor run -p "$S/environments" -i "$id" -a terminus-2 -m openai/gpt-6.1-sol -k 1 \
      -o "$S/jobs/$id" --job-name "$run_name" --yes
done
python3 "$S/scripts/collect_results.py" "$S"
