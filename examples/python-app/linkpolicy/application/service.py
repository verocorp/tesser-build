from __future__ import annotations

import tesser.application as ts

import linkpolicy.application.ports.verdict_repository as verdict_repository
import linkpolicy.application.views as linkpolicy_views
import linkpolicy.client.client as client
import linkpolicy.domain.policy as policy


class LinkPolicyService(ts.ApplicationService):

    def __init__(self, repo: verdict_repository.VerdictRepository) -> None:
        self._repo = repo
        self._policy = policy.Policy()

    def check(self, req: client.CheckRequest) -> client.CheckResponse:
        verdict = self._policy.evaluate(req.target_url)
        self._repo.record(linkpolicy_views.record_request(verdict))
        return linkpolicy_views.check_response(verdict)

    def list_verdicts(self, req: client.ListVerdictsRequest) -> client.ListVerdictsResponse:
        listed = self._repo.all(verdict_repository.ListVerdictsRequest())
        views = tuple(linkpolicy_views.verdict_view(v) for v in listed.verdicts)
        return client.ListVerdictsResponse(verdicts=views)
