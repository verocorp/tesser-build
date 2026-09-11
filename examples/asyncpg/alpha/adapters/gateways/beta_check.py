from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports as ports
import beta.client as beta_client


class BetaCheckGateway(ts.Gateway):

    def __init__(self, beta_client: beta_client.BetaClient) -> None:
        self._beta_client = beta_client

    async def check(self, check_request: ports.CheckRequest) -> ports.CheckResponse:
        try:
            check_response = await self._beta_client.check(
                beta_client.CheckRequest(key=check_request.name)
            )
        except beta_client.Unavailable as beta_error:
            raise ports.BetaUnavailable(beta_error.message) from beta_error
        verdict = ports.Verdict.OK if check_response.held == "yes" else ports.Verdict.REFUSED
        return ports.CheckResponse(verdict=verdict)
