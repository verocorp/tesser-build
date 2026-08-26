from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.gateways.beta_check as gateway
import alpha.application.ports.beta_check as port
import beta.client.client as beta_client


@ts.fake
class FakeBetaClient(beta_client.Client):

    def __init__(self, held: str) -> None:
        self._held = held

    def check(self, request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held=self._held)


def test_a_held_key_is_an_ok_verdict() -> None:
    checked = gateway.BetaCheckGateway(FakeBetaClient("yes")).check(port.CheckRequest(id="w"))
    assert checked.verdict is port.Verdict.OK


def test_an_unheld_key_is_refused() -> None:
    checked = gateway.BetaCheckGateway(FakeBetaClient("no")).check(port.CheckRequest(id="w"))
    assert checked.verdict is port.Verdict.REFUSED
