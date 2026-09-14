from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports as ports
import beta.client as beta_client


class BetaCheckGateway(ts.Gateway):

    def __init__(self, beta_client: beta_client.BetaClient) -> None:
        self._beta_client = beta_client

    async def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        check_key_response = await self._beta_client.check_key(
            beta_client.CheckKeyRequest(key=check_name_request.name)
        )
        outcome = (
            ports.CheckNameOutcome.OK
            if check_key_response.held == "yes"
            else ports.CheckNameOutcome.REFUSED
        )
        return ports.CheckNameResponse(outcome=outcome)
