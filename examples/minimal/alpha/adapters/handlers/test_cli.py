from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.client as client
import protocol


@ts.fake
class FakeClient(client.AlphaClient):

    def add(self, add_request: client.AddRequest) -> client.AddResponse:
        return client.AddResponse(name=add_request.name, standing="kept")


class TestHandler:

    def test_add_prints_the_added_name(self) -> None:
        handler = handlers.Handler(FakeClient())
        cli_response = handler.add(protocol.CliRequest(args=("a", "p")))
        assert cli_response.line == protocol.Line(text="a")
