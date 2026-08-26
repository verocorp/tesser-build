from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports.beta_check as beta_check
import beta.client.client as beta_client
import tesser.application as application  # tesser:debt TB050


class MapToCheckResponse(application.Mapper, beta_check.CheckResponse):  # tesser:debt TB052

    def __init__(self, answer: beta_client.CheckResponse) -> None:
        super().__init__(
            verdict=beta_check.Verdict.OK if answer.held == "yes" else beta_check.Verdict.REFUSED
        )


class BetaCheckGateway(ts.Gateway):

    def __init__(self, beta: beta_client.Client) -> None:
        self._beta = beta

    def check(self, request: beta_check.CheckRequest) -> beta_check.CheckResponse:
        answer = self._beta.check(beta_client.CheckRequest(key=request.name))
        return MapToCheckResponse(answer)
