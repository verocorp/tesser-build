from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.gateways as gateways
import alpha.application.ports as ports
import beta.client as beta_client


@ts.fake
class FakeBetaClient(beta_client.BetaClient):

    def check_key(self, check_key_request: beta_client.CheckKeyRequest) -> beta_client.CheckKeyResponse:
        return beta_client.CheckKeyResponse(held="no")


class TestBetaCheckGateway:

    def test_an_unheld_key_is_refused(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(FakeBetaClient())
        check_name_response = beta_check_gateway.check_name(ports.CheckNameRequest(name="a"))
        assert check_name_response.outcome is ports.CheckNameOutcome.REFUSED
