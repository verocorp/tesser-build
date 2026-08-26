from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.beta_check as beta_check
import beta.client.client as beta_client
import tesser.errors as errors


class BetaCheckGateway(ts.Gateway):

    def __init__(self, beta: beta_client.Client) -> None:
        self._beta = beta

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        try:
            answer = self._beta.check(beta_client.CheckRequest(key=request.id))
        except errors.DomainError as e:
            raise errors.InfraError("beta refused the check") from e
        verdict = beta_check.Verdict.OK if answer.held == "yes" else beta_check.Verdict.REFUSED
        return beta_check.CheckResponse(verdict=verdict)
