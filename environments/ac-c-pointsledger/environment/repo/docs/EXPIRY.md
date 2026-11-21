# Points expiry (LOY-412)

Product decision (approved 2026-11-12): points expire **365 days after they are
earned**, and redemptions spend the oldest points first.

## Lots

Every `earn` transaction creates a *lot*:

| column | meaning |
|---|---|
| `id` | integer primary key |
| `member_id` | owner |
| `earn_txn_id` | the `transactions.id` that created it (unique) |
| `earned_at` | timestamp of the earn transaction |
| `expires_at` | `earned_at` + 365 days (same time of day), same timestamp format |
| `original` | points earned |
| `remaining` | points not yet redeemed or expired |

A lot is **expired at time `t`** when `t >= expires_at`.

Add a table `point_lots` with exactly these columns in migration `0003`.

## Behaviour

* `Ledger.earn` records the transaction and creates its lot.
* `Ledger.balance(member, at)` = sum of `remaining` over the member's lots that
  were earned at or before `at` and are not expired at `at`.
* `Ledger.redeem(member, points, at)` spends from lots that are not expired at
  `at`, oldest `earned_at` first (ties: lower lot id first). If those lots hold
  fewer than `points`, raise `InsufficientPoints` and change nothing.
* `Ledger.expire_due(at)` (new) closes out every lot, of every member, that is
  expired at `at` and still has `remaining > 0`: it writes a transaction of kind
  `expire` with `points = -remaining` and `at = the lot's expires_at`, and sets
  `remaining` to 0. It returns the number of points expired. Running it again
  for the same `at` changes nothing.
* Statements gain an `expired` bucket (absolute points expired in the period);
  `closing = opening + earned - redeemed - expired`.

## Migration 0003

* `transactions.kind` must accept `'expire'` (it is currently restricted by a
  CHECK constraint), without losing or renumbering existing rows.
* Create `point_lots` and backfill it from history: replay each member's
  transactions in time order; every `earn` opens a lot; every `redeem` spends
  from lots not expired at the redemption time, oldest first. If a historical
  redemption is larger than what is unexpired under the new rule, take the
  shortfall from the oldest lots that still have points regardless of expiry
  (history is never rewritten and the migration must not fail).
* The backfill does **not** write `expire` transactions; the daily
  `expire_due` job does that after the release.
* Existing balances therefore only change once `expire_due` runs.
