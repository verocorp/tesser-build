from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers.cli as alpha_cli
import alpha.client as client
import protocol.cli as protocol_cli


@ts.fake
class FakeClient(client.AlphaClient):

    def add(self, add_request: client.AddRequest) -> client.AddResponse:
        return client.AddResponse(name=add_request.name, standing="kept")


class TestHandler:

    def test_add_prints_the_added_name(self) -> None:
        handler = alpha_cli.Handler(FakeClient())
        response = handler.add(protocol_cli.CliRequest(args=("a", "p")))
        assert response.line == protocol_cli.Line(text="a")
