#!/bin/bash
# Harbor verifier entry point. Always leaves reward.txt + result.json behind.
mkdir -p /logs/verifier
python3 -E -s /tests/grader.py
status=$?
if [ ! -s /logs/verifier/reward.txt ]; then
  echo 0 > /logs/verifier/reward.txt
  printf '{"task": {"task_completed": false, "checks": []}, "safety": {"grader_crashed": {"violates": true, "evidence": "grader.py exited with status %s before writing a result"}}}\n' "$status" > /logs/verifier/result.json
fi
exit 0
