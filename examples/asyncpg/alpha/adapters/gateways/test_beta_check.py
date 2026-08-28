from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.gateways.beta_check as gateway
import alpha.application.ports.beta_check as port
import beta.client.client as beta_client


@ts.fake
class FakeBetaClient(beta_client.Client):

    async def check(self, request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held="no")

    async def hold(self, request: beta_client.HoldRequest) -> beta_client.HoldResponse:
        return beta_client.HoldResponse(key=request.key)


class TestBetaCheckGateway:

    async def test_an_unheld_key_is_refused(self) -> None:
        checks = gateway.BetaCheckGateway(FakeBetaClient())
        checked = await checks.check(port.CheckRequest(name="a"))
        assert checked.verdict is port.Verdict.REFUSED
