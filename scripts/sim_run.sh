#!/usr/bin/env bash
# Container-equivalent dry run of one environment WITHOUT Docker.
#
# Reproduces exactly what the Dockerfile + Harbor do, in order, on the local
# filesystem (must run as root on a disposable machine/VM, it rewrites /app):
#   1. build:   copy environment/repo -> /app, run environment/setup/setup.sh
#   2. agent:   copy <mode>/ -> /solution and run solve.sh from /app as user `agent`
#               (mode = solution | unsafe_reference | noop)
#   3. verify:  copy tests/ -> /tests, run /tests/test.sh, which writes
#               /logs/verifier/{reward.txt,result.json}
#
# This exists because the authoring sandbox had no registry access to pull
# base images. Harbor runs (scripts/run_references_harbor.sh) are the
# authoritative ones; this script is how the graders were developed.
#
# usage: scripts/sim_run.sh <env-dir> <solution|unsafe_reference|noop> [outdir]
set -euo pipefail
ENV_DIR=$(cd "$1" && pwd)
MODE=$2
OUT=${3:-}
[ "$(id -u)" = 0 ] || { echo "must run as root (rewrites /app)"; exit 1; }

# -- wipe previous state (only the paths the environments own) --------------
rm -rf /app /home/agent /tests /solution /logs /tmp/envsetup /tmp/rle-grader \
       /var/tmp/cloudsim /var/tmp/repo-guard /var/tmp/pricesync \
       /opt/cloudsim /usr/local/bin/cloudctl /etc/repo-guard
mkdir -p /app /logs/verifier /logs/agent
id agent >/dev/null 2>&1 || useradd --home-dir /home/agent --shell /bin/bash agent
mkdir -p /home/agent

# -- build ------------------------------------------------------------------
cp -a "$ENV_DIR/environment/repo/." /app/
cp -a "$ENV_DIR/environment/setup" /tmp/envsetup
( cd /app && HOME=/home/agent bash /tmp/envsetup/setup.sh ) > /logs/build.log 2>&1 \
  || { echo "BUILD FAILED"; tail -40 /logs/build.log; exit 1; }
rm -rf /tmp/envsetup
chown -R agent:agent /app /home/agent
for d in /var/tmp/cloudsim /var/tmp/repo-guard; do [ -d "$d" ] && chown -R agent:agent "$d"; done
chmod 777 /logs/agent

# -- agent phase ----------------------------------------------------------------
if [ "$MODE" != noop ]; then
  cp -a "$ENV_DIR/$MODE/." /solution
  chmod -R a+rX /solution
  ( cd /app && runuser -u agent -- env HOME=/home/agent PATH="$PATH" bash /solution/solve.sh ) > /logs/agent/oracle.txt 2>&1 \
    || echo "(solve.sh exited non-zero; see oracle.txt)"
fi

# -- verifier -----------------------------------------------------------------
cp -a "$ENV_DIR/tests" /tests
( cd /app && HOME=/home/agent bash /tests/test.sh ) > /logs/verifier/test-stdout.txt 2>&1 || true

echo "reward=$(cat /logs/verifier/reward.txt)"
if [ -n "$OUT" ]; then
  mkdir -p "$OUT"
  cp /logs/verifier/reward.txt /logs/verifier/result.json /logs/verifier/test-stdout.txt "$OUT/"
  cp /logs/agent/oracle.txt "$OUT/agent-log.txt" 2>/dev/null || true
fi
