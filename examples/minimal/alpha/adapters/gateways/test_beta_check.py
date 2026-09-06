from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.gateways as gateways
import alpha.application.ports as ports
import beta.client as client


@ts.fake
class FakeBetaClient(client.BetaClient):

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        return client.CheckResponse(held="no")


class TestBetaCheckGateway:

    def test_an_unheld_key_is_refused(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(FakeBetaClient())
        check_response = beta_check_gateway.check(ports.CheckRequest(name="a"))
        assert check_response.verdict is ports.Verdict.REFUSED
