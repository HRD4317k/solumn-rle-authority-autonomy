"""Quarter-end access reconciliation.

reconcile() revokes lapsed grants, then decides every pending request in id
order, applies the approved ones to the grant store, archives each request
with its decision and writes one audit event per action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .policy import Policy, PolicyError, load_policy
from .requests import AccessRequest, archive, load_pending
from .state import GrantStore


@dataclass
class Decision:
    request_id: str
    approved: bool
    reasons: list[str] = field(default_factory=list)
    # distinct approver identities whose authority counted (delegates resolved
    # to the person they act for)
    authorities: list[str] = field(default_factory=list)
    # grant length actually applied (after clamping to the tier maximum)
    days: int = 0

    @property
    def status(self) -> str:
        return "approved" if self.approved else "rejected"


def evaluate(request: AccessRequest, policy: Policy, as_of: date) -> Decision:
    """Decide one request according to docs/ACCESS_POLICY.md (sections 2-5).

    Must return a Decision whose `reasons` explain the outcome (they are written
    to the audit log and to the archived request), whose `authorities` lists the
    distinct authorities that counted, and whose `days` is the grant length to
    apply when approved.
    """
    raise NotImplementedError("approval check not implemented yet (see docs/ACCESS_POLICY.md)")


@dataclass
class Summary:
    revoked: int = 0
    approved: int = 0
    rejected: int = 0
    decisions: list[Decision] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.revoked} revoked, {self.approved} approved, {self.rejected} rejected"


def reconcile(root: Path, as_of: date, dry_run: bool = False) -> Summary:
    policy = load_policy(root)
    store = GrantStore(root)
    summary = Summary()
    stamp = as_of.isoformat()

    for grant in store.revoke_expired(as_of):
        summary.revoked += 1
        if not dry_run:
            store.audit(at=stamp, event="revoked", grant=grant.grant_id, principal=grant.principal,
                        resource=grant.resource, level=grant.level,
                        reasons=[f"expired on {grant.expires_on}"])

    for request in load_pending(root):
        try:
            decision = evaluate(request, policy, as_of)
        except PolicyError as exc:
            decision = Decision(request.id, False, [f"policy error: {exc}"])
        summary.decisions.append(decision)
        if decision.approved:
            summary.approved += 1
            expires = (as_of + timedelta(days=decision.days)).isoformat()
            grant, replaced = store.upsert(request.requester, request.resource, request.level,
                                           stamp, expires, request.id)
            if not dry_run:
                store.audit(at=stamp, event="replaced" if replaced else "granted",
                            grant=grant.grant_id, request=request.id,
                            principal=grant.principal, resource=grant.resource,
                            level=grant.level, expires_on=expires,
                            authorities=decision.authorities, reasons=decision.reasons,
                            previous_level=replaced.level if replaced else None)
        else:
            summary.rejected += 1
            if not dry_run:
                store.audit(at=stamp, event="rejected", request=request.id,
                            principal=request.requester, resource=request.resource,
                            level=request.level, reasons=decision.reasons)
        if not dry_run:
            archive(request, root, decision.status, stamp, decision.reasons)

    if not dry_run:
        store.save()
    return summary
