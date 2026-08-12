from __future__ import annotations

from typing import Protocol

import tesser.application as ts

import linkpolicy.client.client as client
import linkpolicy.domain.policy as policy


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
        self._policy = policy.Policy()

    def check(self, req: client.CheckRequest) -> client.CheckResponse:
        verdict = self._policy.evaluate(req.target_url)
        self._repo.record(
            VerdictParts(
                str(verdict.target_url), str(verdict.allowed) == "allowed", str(verdict.reason)
            )
        )
        return client.CheckResponse(allowed=str(verdict.allowed) == "allowed", reason=str(verdict.reason))

    def list_verdicts(self, req: client.ListVerdictsRequest) -> client.ListVerdictsResponse:
        views = tuple(client.VerdictView(p.target_url, p.allowed, p.reason) for p in self._repo.all())
        return client.ListVerdictsResponse(verdicts=views)
