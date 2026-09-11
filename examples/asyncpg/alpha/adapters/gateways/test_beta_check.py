from __future__ import annotations

import pytest

import tesser.testing as ts

import alpha.adapters.gateways as gateways
import alpha.application.ports as ports
import beta.client as beta_client


@ts.fake
class FakeBetaClient(beta_client.BetaClient):

    def __init__(self, held: str) -> None:
        self._held = held

    async def check(self, check_request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held=self._held)

    async def hold(self, hold_request: beta_client.HoldRequest) -> beta_client.HoldResponse:
        return beta_client.HoldResponse(key=hold_request.key)


@ts.fake
class FakeRefusingBetaClient(beta_client.BetaClient):

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def check(self, check_request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        raise self._error

    async def hold(self, hold_request: beta_client.HoldRequest) -> beta_client.HoldResponse:
        raise self._error


class TestBetaCheckGateway:

    async def test_an_unheld_key_is_refused(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(FakeBetaClient(held="no"))
        check_response = await beta_check_gateway.check(ports.CheckRequest(name="a"))
        assert check_response.verdict is ports.Verdict.REFUSED

    async def test_a_held_key_is_approved(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(FakeBetaClient(held="yes"))
        check_response = await beta_check_gateway.check(ports.CheckRequest(name="a"))
        assert check_response.verdict is ports.Verdict.OK

    async def test_a_beta_that_cannot_answer_is_the_ports_unavailable(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(
            FakeRefusingBetaClient(beta_client.Unavailable("the key store is unavailable"))
        )
        with pytest.raises(ports.BetaUnavailable) as caught:
            await beta_check_gateway.check(ports.CheckRequest(name="a"))
        assert isinstance(caught.value.__cause__, beta_client.Unavailable)

    async def test_a_beta_rejection_is_our_bug_and_leaves_the_gateway_untranslated(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(
            FakeRefusingBetaClient(beta_client.Rejected("empty_key", "a key is never empty"))
        )
        with pytest.raises(beta_client.Rejected):
            await beta_check_gateway.check(ports.CheckRequest(name="a"))
