#!/usr/bin/env bash
# Pin every environment's base image to the digest it resolves to today.
# Run once on a machine with Docker + registry access, then commit the result.
set -euo pipefail
S=$(cd "$(dirname "$0")/.." && pwd)
for df in "$S"/environments/*/environment/Dockerfile; do
  img=$(awk '/^FROM /{print $2; exit}' "$df")
  case "$img" in *@sha256:*) echo "already pinned: $df"; continue;; esac
  docker pull -q "$img" >/dev/null
  digest=$(docker inspect --format '{{index .RepoDigests 0}}' "$img" | sed 's/.*@//')
  sed -i.bak "1s|^FROM .*|FROM ${img}@${digest}|" "$df" && rm -f "$df.bak"
  echo "pinned $(basename "$(dirname "$(dirname "$df")")"): ${img}@${digest}"
done
