from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers.cli as cli
import alpha.client.client as client
import protocol.cli as protocol_cli


@ts.fake
class FakeClient(client.Client):

    async def add(self, request: client.AddRequest) -> client.AddResponse:
        return client.AddResponse(name=request.name, standing="kept")

    async def take(self, request: client.TakeRequest) -> client.TakeResponse:
        return client.TakeResponse(name=request.name, part=request.part, standing="kept")

    async def find(self, request: client.FindRequest) -> client.FindResponse:
        return client.FindResponse(found="no")


class TestHandler:

    async def test_add_prints_the_added_name(self) -> None:
        handler = cli.Handler(FakeClient())
        response = await handler.add(protocol_cli.CliRequest(args=("a", "p")))
        assert response.line == protocol_cli.Line(text="a")
