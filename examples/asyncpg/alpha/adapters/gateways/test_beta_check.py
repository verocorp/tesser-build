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

    async def check_key(self, check_key_request: beta_client.CheckKeyRequest) -> beta_client.CheckKeyResponse:
        return beta_client.CheckKeyResponse(held=self._held)

    async def hold_key(self, hold_key_request: beta_client.HoldKeyRequest) -> beta_client.HoldKeyResponse:
        return beta_client.HoldKeyResponse(key=hold_key_request.key)


@ts.fake
class FakeRefusingBetaClient(beta_client.BetaClient):

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def check_key(self, check_key_request: beta_client.CheckKeyRequest) -> beta_client.CheckKeyResponse:
        raise self._error

    async def hold_key(self, hold_key_request: beta_client.HoldKeyRequest) -> beta_client.HoldKeyResponse:
        raise self._error


class TestBetaCheckGateway:

    async def test_an_unheld_key_is_refused(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(FakeBetaClient(held="no"))
        check_name_response = await beta_check_gateway.check_name(ports.CheckNameRequest(name="a"))
        assert check_name_response.outcome is ports.CheckNameOutcome.REFUSED

    async def test_a_held_key_is_approved(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(FakeBetaClient(held="yes"))
        check_name_response = await beta_check_gateway.check_name(ports.CheckNameRequest(name="a"))
        assert check_name_response.outcome is ports.CheckNameOutcome.OK

    async def test_a_beta_rejection_is_our_bug_and_leaves_the_gateway_untranslated(self) -> None:
        beta_check_gateway = gateways.BetaCheckGateway(
            FakeRefusingBetaClient(beta_client.KeyRejected("empty_key", "a key is never empty"))
        )
        with pytest.raises(beta_client.KeyRejected):
            await beta_check_gateway.check_name(ports.CheckNameRequest(name="a"))
