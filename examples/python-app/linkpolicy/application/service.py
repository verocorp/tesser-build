from __future__ import annotations

import tesser.application as ts

import linkpolicy.application.ports.verdict_repository as verdict_repository
import linkpolicy.client.client as client
import linkpolicy.domain.policy as policy


class LinkPolicyService(ts.ApplicationService):

    def __init__(self, repo: verdict_repository.VerdictRepository) -> None:
        self._repo = repo
        self._policy = policy.Policy(policy.PolicySpec())

    def check(self, req: client.CheckRequest) -> client.CheckResponse:
        target_url = policy.TargetURL(req.target_url)
        target_url_text = str(target_url)
        verdict = self._policy.evaluate(target_url_text)
        verdict_target_url = str(verdict.target_url)
        verdict_reason = str(verdict.reason)
        allowed = str(verdict.allowed) == "allowed"
        decision = (
            verdict_repository.VerdictDecision.ALLOWED
            if allowed
            else verdict_repository.VerdictDecision.DENIED
        )
        record_verdict_request = verdict_repository.RecordVerdictRequest(
            target_url=verdict_target_url, decision=decision, reason=verdict_reason
        )
        self._repo.record(record_verdict_request)
        return client.CheckResponse(allowed=allowed, reason=verdict_reason)

    def list_verdicts(self, req: client.ListVerdictsRequest) -> client.ListVerdictsResponse:
        listed = self._repo.all(verdict_repository.ListVerdictsRequest())
        views: list[client.VerdictView] = []
        for record in listed.verdicts:
            record_allowed = record.decision == verdict_repository.VerdictDecision.ALLOWED
            view = client.VerdictView(record.target_url, record_allowed, record.reason)
            views.append(view)
        listed_views = tuple(views)
        return client.ListVerdictsResponse(verdicts=listed_views)
