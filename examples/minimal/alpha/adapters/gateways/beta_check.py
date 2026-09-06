from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports as ports
import beta.client as client


class MapToCheckResponse(ts.Mapper, ports.CheckResponse):

    def __init__(self, check_response: client.CheckResponse) -> None:
        super().__init__(
            verdict=ports.Verdict.OK if check_response.held == "yes" else ports.Verdict.REFUSED
        )


class BetaCheckGateway(ts.Gateway):

    def __init__(self, beta_client: client.BetaClient) -> None:
        self._beta_client = beta_client

    def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        check_response = self._beta_client.check(client.CheckRequest(key=check_request.name))
        return MapToCheckResponse(check_response)
