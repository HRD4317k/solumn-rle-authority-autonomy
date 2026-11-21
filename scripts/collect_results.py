"""Copy reward.txt / result.json / logs of every Harbor trial under jobs/ into
results/<env>/harbor/<job-name>/<trial>/ and print a summary table."""
import json
import shutil
import sys
from pathlib import Path

S = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
rows = []
for reward in sorted((S / "jobs").glob("*/*/*/verifier/reward.txt")):
    trial = reward.parent.parent
    job = trial.parent
    env = job.parent.name
    dest = S / "results" / env / "harbor" / job.name / trial.name
    dest.mkdir(parents=True, exist_ok=True)
    for sub in ("verifier", "agent"):
        if (trial / sub).exists():
            shutil.copytree(trial / sub, dest / sub, dirs_exist_ok=True)
    for f in ("result.json", "config.json", "trial.log"):
        if (trial / f).exists():
            shutil.copy(trial / f, dest / f"trial-{f}")
    res = trial / "verifier" / "result.json"
    data = json.loads(res.read_text()) if res.exists() else {}
    viol = [k for k, v in data.get("safety", {}).items() if v.get("violates")]
    rows.append((env, job.name, reward.read_text().strip(),
                 data.get("task", {}).get("task_completed"), ",".join(viol) or "-"))
w = max([len(r[0]) for r in rows] + [3])
for r in rows:
    print(f"{r[0]:<{w}}  {r[1]:<28} reward={r[2]} task_completed={r[3]} violations={r[4]}")
