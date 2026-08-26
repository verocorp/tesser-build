from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers.cli as cli
import alpha.client.client as client
import protocol.cli as protocol_cli


@ts.fake
class FakeClient(client.Client):

    def add(self, request: client.AddRequest) -> client.AddResponse:
        return client.AddResponse(name=request.name)


class TestHandler:

    def test_add_prints_the_added_name(self) -> None:
        handler = cli.Handler(FakeClient())
        response = handler.add(protocol_cli.CliRequest(args=("a", "p")))
        assert response.line == protocol_cli.Line(text="a")
