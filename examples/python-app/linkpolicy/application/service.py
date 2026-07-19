from __future__ import annotations

from typing import Protocol

from linkpolicy.client import CheckRequest, CheckResponse, VerdictView
from linkpolicy.domain.policy import Policy, Verdict


class VerdictRepository(Protocol):

    def record(self, verdict: Verdict) -> None: ...

    def all(self) -> tuple[Verdict, ...]: ...


class LinkPolicyService:
    def __init__(self, repo: VerdictRepository, policy: Policy) -> None:
        self._repo = repo
        self._policy = policy

    def check(self, req: CheckRequest) -> CheckResponse:
        verdict = self._policy.evaluate(req.target_url)
        self._repo.record(verdict)
        return CheckResponse(allowed=verdict.allowed, reason=verdict.reason)

    def list_verdicts(self) -> tuple[VerdictView, ...]:
        return tuple(
            VerdictView(v.target_url, v.allowed, v.reason) for v in self._repo.all()
        )
