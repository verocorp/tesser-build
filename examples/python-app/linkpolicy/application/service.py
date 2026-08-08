from __future__ import annotations

from typing import Protocol

import tesser.application as ts

from linkpolicy.client.client import (
    CheckRequest,
    CheckResponse,
    ListVerdictsRequest,
    ListVerdictsResponse,
    VerdictView,
)
from linkpolicy.domain.policy import Policy


class VerdictParts(ts.Parts):

    def __init__(self, target_url: str, allowed: bool, reason: str) -> None:
        self.target_url = target_url
        self.allowed = allowed
        self.reason = reason


class VerdictRepository(ts.Port, Protocol):

    def record(self, parts: VerdictParts) -> None: ...

    def all(self) -> tuple[VerdictParts, ...]: ...


class LinkPolicyService(ts.ApplicationService):

    def __init__(self, repo: VerdictRepository) -> None:
        self._repo = repo
        self._policy = Policy()

    def check(self, req: CheckRequest) -> CheckResponse:
        verdict = self._policy.evaluate(req.target_url)
        self._repo.record(
            VerdictParts(
                str(verdict.target_url), str(verdict.allowed) == "allowed", str(verdict.reason)
            )
        )
        return CheckResponse(allowed=str(verdict.allowed) == "allowed", reason=str(verdict.reason))

    def list_verdicts(self, req: ListVerdictsRequest) -> ListVerdictsResponse:
        views = tuple(VerdictView(p.target_url, p.allowed, p.reason) for p in self._repo.all())
        return ListVerdictsResponse(verdicts=views)
