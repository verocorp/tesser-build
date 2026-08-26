from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.gateways.beta_check as gateway
import alpha.application.ports.beta_check as port
import beta.client.client as beta_client


@ts.fake
class SampledBetaClient(beta_client.Client):

    def check(self, request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held="yes")


def test_a_sampled_answer_maps_to_a_verdict() -> None:
    checked = gateway.BetaCheckGateway(SampledBetaClient()).check(port.CheckRequest(name="a"))
    assert checked.verdict is port.Verdict.OK
