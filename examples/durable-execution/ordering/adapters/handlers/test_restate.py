from __future__ import annotations

import asyncio
import typing

import restate
import tesser.testing as ts

import ordering.adapters.handlers.restate as restate_handlers
import ordering.client.client as client
import protocol.durable as durable


@ts.fake
class FakeActions(client.Actions):

    def __init__(self) -> None:
        self.quoted: list[client.QuoteRequest] = []

    def quote(self, request: client.QuoteRequest) -> client.QuoteResponse:
        self.quoted.append(request)
        return client.QuoteResponse(cents=250)


class TestRestateHandlers:

    def test_it_declares_one_workflow_and_one_service(self) -> None:
        handlers = restate_handlers.RestateHandlers(FakeActions())
        assert [d.name for d in handlers.definitions()] == ["Ordering", "OrderingActions"]

    def test_each_definition_carries_the_handler_named_for_its_function(self) -> None:
        handlers = restate_handlers.RestateHandlers(FakeActions())
        assert [sorted(d.handlers) for d in handlers.definitions()] == [["run"], ["quote"]]

    def test_the_quote_handler_answers_the_cents_the_actions_gave_it(self) -> None:
        fake = FakeActions()
        handlers = restate_handlers.RestateHandlers(fake)

        async def call() -> durable.QuoteResponse:
            return await handlers.quote(
                typing.cast(restate.Context, None), durable.QuoteRequest(sku="widget")
            )

        assert asyncio.run(call()) == durable.QuoteResponse(cents=250)
        assert [q.sku for q in fake.quoted] == ["widget"]
