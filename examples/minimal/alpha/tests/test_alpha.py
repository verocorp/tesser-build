from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers.cli as cli
import alpha.client.client as client
import alpha.component.component as component
import alpha.component.config as config
import beta.client.client as beta_client
import protocol.cli as protocol_cli
import tesser.serialization as serialization


@ts.fake
class FakeBetaClient(beta_client.Client):

    def check(self, request: beta_client.CheckRequest) -> beta_client.CheckResponse:
        return beta_client.CheckResponse(held="yes")


@ts.helper
def add_args(id: str = "w", name: str = "a", count: str = "1") -> protocol_cli.CliRequest:
    return protocol_cli.CliRequest(args=(id, name, count))


def test_a_cli_add_reaches_the_wired_service() -> None:
    wired = component.Alpha(config.Config(config.Spec(storage="memory")), FakeBetaClient())
    handler = cli.Handler(wired.client)
    response = handler.add(add_args())
    assert response.line.text == serialization.canonical_str("w")
    got = wired.client.get(client.GetRequest(id="w"))
    assert tuple(view.name for view in got.wholes) == ("a",)
    wired.close()
