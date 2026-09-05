from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.gateways.beta_check as gateway
import alpha.application.ports as ports
import beta.client as client


@ts.fake
class FakeBetaClient(client.Client):

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        return client.CheckResponse(held="no")


class TestBetaCheckGateway:

    def test_an_unheld_key_is_refused(self) -> None:
        beta_check_gateway = gateway.BetaCheckGateway(FakeBetaClient())
        checked = beta_check_gateway.check(ports.CheckRequest(name="a"))
        assert checked.verdict is ports.Verdict.REFUSED
