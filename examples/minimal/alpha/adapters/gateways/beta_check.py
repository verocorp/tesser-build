from __future__ import annotations

import tesser.adapters as ts

import alpha.application.ports as ports
import beta.client as beta_client


class MapToCheckNameResponse(ts.Mapper, ports.CheckNameResponse):

    def __init__(self, check_key_response: beta_client.CheckKeyResponse) -> None:
        super().__init__(
            outcome=ports.CheckNameOutcome.OK if check_key_response.held == "yes" else ports.CheckNameOutcome.REFUSED
        )


class BetaCheckGateway(ts.Gateway):

    def __init__(self, beta_client: beta_client.BetaClient) -> None:
        self._beta_client = beta_client

    def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        check_key_response = self._beta_client.check_key(beta_client.CheckKeyRequest(key=check_name_request.name))
        return MapToCheckNameResponse(check_key_response)
