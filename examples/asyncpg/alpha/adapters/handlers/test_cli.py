from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.client as client
import protocol


@ts.fake
class FakeClient(client.AlphaClient):

    async def add(self, add_request: client.AddRequest) -> client.AddResponse:
        return client.AddResponse(name=add_request.name, part=add_request.part, standing="kept")

    async def take(self, take_request: client.TakeRequest) -> client.TakeResponse:
        return client.TakeResponse(name=take_request.name, part=take_request.part, standing="kept")

    async def find(self, find_request: client.FindRequest) -> client.FindResponse:
        return client.FindResponse(found="no")


class TestHandler:

    async def test_add_prints_the_name_the_part_and_the_standing(self) -> None:
        handler = handlers.Handler(FakeClient())
        cli_response = await handler.add(protocol.CliRequest(args=("a", "p")))
        assert cli_response.line == protocol.Line(text="a p kept")
