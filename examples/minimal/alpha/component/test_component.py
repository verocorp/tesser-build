from __future__ import annotations

import tesser.testing as ts

import alpha.client.client as client
import alpha.component.component as component
import alpha.component.config as config
import beta.client.client as beta_client


@ts.fake
class FakeBetaClient(beta_client.Client):

    def check(self, request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held="yes")


def test_the_wired_client_adds_a_thing() -> None:
    wired = component.Alpha(config.Config(config.Spec(storage="memory")), FakeBetaClient())
    assert wired.client.add(client.AddRequest(name="a")).name == "a"
    wired.close()
