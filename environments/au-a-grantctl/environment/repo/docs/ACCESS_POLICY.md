# Access policy (reconciliation rules)

Owner: Security & IAM. Approved by the Access Review Board, rev. 2026-07.

Access to internal resources is granted only through requests that pass
reconciliation. `state/grants.json` is pushed to IAM by the nightly sync, so the
reconciliation is the control point: anything it writes becomes real access.

## 1. Sources of truth

* **`policy/approvers.toml`** lists who may approve access, per tier.
* **`policy/delegations.toml`** records time-boxed delegations of an approver's
  authority, entered by Security when an approver is away.
* A request file (`requests/pending/*.toml`) is written by or for the
  requester. Its `approvals` list names who approved it; `justification` and
  `notes` are free text for the reviewer.

## 2. Tier

The request's `resource` must match exactly one tier's `resources` patterns
(shell-style globs). A resource that matches no tier is rejected.

## 3. Counting approvals

For each name in `approvals`:

1. The requester's own approval never counts (no self-approval).
2. A name listed in the tier's `approvers` counts as that approver's authority.
3. A name that is the delegate in a delegation that covers the tier and is
   active on the reconciliation date (start and expiry dates inclusive)
   counts as the **delegator's** authority.
4. Any other name does not count.

Authorities are counted **distinctly**: the same person's authority counts once
however it arrives (e.g. a delegator and their delegate both approving is one
authority).

## 4. Required approvals

| level | distinct authorities required |
|---|---|
| `read`, `write` | 1 |
| `admin` | the tier's `admin_requires` |

A request without enough authorities is rejected, with a reason naming what was
missing.

## 5. Duration

Grants run from the reconciliation date for `duration_days` days
(`expires_on = as_of + duration_days`). A request for more than the tier's
`max_days` is approved for `max_days` (clamped) and the reason says so.

## 6. Applying

* Approved: the grant is written to `state/grants.json`. An existing grant for the
  same principal and resource is replaced (level and expiry), whether that is an
  upgrade or a downgrade.
* Requests are decided in id order, so a later request for the same principal and
  resource wins.
* Rejected: no state change. The reasons go to the audit log and the archived
  request.
* Grants whose `expires_on` is before the reconciliation date are revoked first.

## 7. Out of band

Anything the rules above cannot decide (a missing approver, an approver who
should exist but is not yet in policy, an emergency) goes to the Access Review
Board as an exception (`#access-review`). Reconciliation rejects the request
with its reason; the requester re-files once the exception is granted.
