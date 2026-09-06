from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.gateways as gateways
import alpha.application.ports as ports
import beta.client as client


@ts.fake
class FakeBetaClient(client.BetaClient):

    def __init__(self, held: str) -> None:
        self._held = held

    async def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        return client.CheckResponse(held=self._held)

    async def hold(self, hold_request: client.HoldRequest) -> client.HoldResponse:
        return client.HoldResponse(key=hold_request.key)


class TestBetaCheckGateway:

    async def test_an_unheld_key_is_refused(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(FakeBetaClient(held="no"))
        check_response = await beta_check_gateway.check(ports.CheckRequest(name="a"))
        assert check_response.verdict is ports.Verdict.REFUSED

    async def test_a_held_key_is_approved(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(FakeBetaClient(held="yes"))
        check_response = await beta_check_gateway.check(ports.CheckRequest(name="a"))
        assert check_response.verdict is ports.Verdict.OK
