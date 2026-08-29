from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.gateways.beta_check as gateway
import alpha.application.ports.beta_check as port
import beta.client.client as beta_client


@ts.fake
class FakeBetaClient(beta_client.Client):

    def __init__(self, held: str) -> None:
        self._held = held

    async def check(self, request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held=self._held)

    async def hold(self, request: beta_client.HoldRequest) -> beta_client.HoldResponse:
        return beta_client.HoldResponse(key=request.key)


class TestBetaCheckGateway:

    async def test_an_unheld_key_is_refused(self) -> None:
        checks = gateway.BetaCheckGateway(FakeBetaClient(held="no"))
        checked = await checks.check(port.CheckRequest(name="a"))
        assert checked.verdict is port.Verdict.REFUSED

    async def test_a_held_key_is_approved(self) -> None:
        checks = gateway.BetaCheckGateway(FakeBetaClient(held="yes"))
        checked = await checks.check(port.CheckRequest(name="a"))
        assert checked.verdict is port.Verdict.OK
