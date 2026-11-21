# Runbook: decommissioning an environment

An environment is the set of resources tagged `env=<name>`. A teardown is only
run under an approved change record (`changes/CHG-*.toml`) naming that env.

```
python -m teardown plan --env stg-payments --change CHG-4471          # dry run
python -m teardown run  --env stg-payments --change CHG-4471 --yes
```

## 1. Scope

Only resources whose `env` tag equals the target env are in scope - not ones
with a similar name, and not ones that merely live inside the env's network.

## 2. Ordering

`cloudctl delete` refuses to delete anything that is still referenced (a VPC
with subnets or security groups, a subnet with instances or load balancers, a
security group used by an instance or LB, an instance behind an LB or with a
volume attached, an LB with a DNS record pointing at it). The plan must
therefore delete every resource only after the in-scope resources that
reference it - in practice DNS -> load balancers -> instances -> volumes ->
security groups -> subnets -> VPC, but derive it from the actual references
(`Inventory.dependents`), not from the type names.

* Attached volumes are **detached** first (a `detach` step before the
  instance's delete), then deleted.
* Buckets are deleted with `--force` (they hold build artefacts).
* Resources tagged `retain=true` are **skipped** (legal hold) and reported.
* Snapshots are never deleted by a teardown (the backup lifecycle expires
  them); they are not part of the plan.
* A step's `after` lists the resources whose steps must succeed first, so that
  when something can't be removed, everything that depends on it is reported
  as blocked instead of failing noisily.
* If a resource is referenced by something **outside** the env, the plan marks
  its delete `blocked_by` those resources.

## 3. Final snapshots

Volumes tagged `backup=required` get a final snapshot before they are deleted:
`cloudctl snapshot <vol> --note "final snapshot: teardown <env> <date>"`. The
snapshot step must succeed (check the new snapshot exists and points at the
volume) before the volume's delete step runs; its outcome detail is the
snapshot id.

## 4. After the run

The run writes `reports/teardown-<env>-<date>.md`. Anything in *Blocked* or
*Failed* needs follow-up with whoever owns the blocking resource; attach the
report to the change record.
