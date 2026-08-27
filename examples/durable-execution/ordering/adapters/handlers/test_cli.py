from __future__ import annotations

import asyncio

import pytest
import tesser.testing as ts

import ordering.adapters.handlers.cli as cli
import ordering.client.client as client
import protocol.cli as protocol_cli


@ts.fake
class FakeClient(client.Client):

    def __init__(self) -> None:
        self.placed: list[client.PlaceRequest] = []

    async def place(self, request: client.PlaceRequest) -> client.PlaceResponse:
        self.placed.append(request)
        return client.PlaceResponse(order_id=request.order_id)


class TestHandler:

    def test_place_prints_the_placed_order_id(self) -> None:
        handler = cli.Handler(FakeClient())
        response = asyncio.run(handler.place(protocol_cli.CliRequest(args=("o1", "widget", "2"))))
        assert response.line == protocol_cli.Line(text="o1")

    def test_place_carries_the_arguments_to_the_client(self) -> None:
        fake = FakeClient()
        asyncio.run(cli.Handler(fake).place(protocol_cli.CliRequest(args=("o1", "widget", "2"))))
        assert [(p.order_id, p.sku, p.quantity) for p in fake.placed] == [("o1", "widget", 2)]

    def test_a_non_numeric_quantity_is_a_usage_error(self) -> None:
        handler = cli.Handler(FakeClient())
        with pytest.raises(protocol_cli.UsageError):
            asyncio.run(handler.place(protocol_cli.CliRequest(args=("o1", "widget", "two"))))
