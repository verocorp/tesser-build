from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers.cli as cli
import alpha.component.component as component
import alpha.component.config as config
import beta.client.client as beta_client
import protocol.cli as protocol_cli
import tesser.serialization as serialization


@ts.fake
class FakeBetaClient(beta_client.Client):

    def check(self, request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held="yes")


def test_a_cli_add_reaches_the_wired_service() -> None:
    wired = component.Alpha(config.Config(config.Spec(storage="memory")), FakeBetaClient())
    response = cli.Handler(wired.client).add(protocol_cli.CliRequest(args=("a",)))
    assert response.line.text == serialization.canonical_str("a")
    wired.close()
