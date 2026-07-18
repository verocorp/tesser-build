"""The linkpolicy application service: convert -> delegate -> persist -> respond.

It satisfies ``linkpolicy.Client`` structurally (same four... two methods, same
DTOs), so ``wiring`` can return it directly as the public Client. The repository
port is declared HERE, beside its only consumer.
"""

from __future__ import annotations

from typing import Protocol

from linkpolicy.client import CheckRequest, CheckResponse, VerdictView
from linkpolicy.domain.policy import Policy, Verdict


class VerdictRepository(Protocol):
    """Outbound port owned by the application, satisfied by an adapter in
    ``adapters/gateways``."""

    def record(self, verdict: Verdict) -> None: ...

    def all(self) -> tuple[Verdict, ...]: ...


class LinkPolicyService:
    def __init__(self, repo: VerdictRepository, policy: Policy) -> None:
        self._repo = repo
        self._policy = policy

    def check(self, req: CheckRequest) -> CheckResponse:
        verdict = self._policy.evaluate(req.target_url)
        self._repo.record(verdict)  # an InfraError here propagates (fail-closed for the caller)
        return CheckResponse(allowed=verdict.allowed, reason=verdict.reason)

    def list_verdicts(self) -> tuple[VerdictView, ...]:
        return tuple(
            VerdictView(v.target_url, v.allowed, v.reason) for v in self._repo.all()
        )
