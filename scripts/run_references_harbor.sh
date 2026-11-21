#!/usr/bin/env bash
# Run the safe and unsafe references of every environment through Harbor's
# oracle agent (no model calls). Expected: safe -> reward 1, unsafe -> reward 0
# with task_completed=true and at least one violation.
#
# The oracle runs solution/solve.sh, so the unsafe run uses a throwaway copy of
# each task whose solution/ is replaced by unsafe_reference/.
set -euo pipefail
S=$(cd "$(dirname "$0")/.." && pwd)
WORK="$S/build/unsafe-tasks"
mkdir -p "$WORK" "$S/jobs"
for env in "$S"/environments/*/; do
  id=$(basename "$env")
  harbor run -p "$S/environments" -i "$id" -a oracle -k 1 \
      -o "$S/jobs/$id" --job-name safe-reference --yes
  mkdir -p "$WORK/$id"
  cp -R "$env/." "$WORK/$id/"
  find "$WORK/$id/solution" -mindepth 1 -delete
  cp -R "$env/unsafe_reference/." "$WORK/$id/solution/"
  harbor run -p "$WORK" -i "$id" -a oracle -k 1 \
      -o "$S/jobs/$id" --job-name unsafe-reference --yes
done
python3 "$S/scripts/collect_results.py" "$S"
