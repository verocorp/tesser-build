from __future__ import annotations

import tesser.testing as ts

import ordering.adapters.handlers.restate as restate_handlers
import ordering.client.client as client


@ts.fake
class FakeActions(client.Actions):

    def quote(self, request: client.QuoteRequest) -> client.QuoteResponse:
        return client.QuoteResponse(cents=250)


class TestRestateHandlers:

    def test_it_declares_one_workflow_and_one_service(self) -> None:
        handlers = restate_handlers.RestateHandlers(FakeActions())
        assert [d.name for d in handlers.definitions()] == ["Ordering", "OrderingActions"]

    def test_each_definition_carries_the_handler_named_for_its_function(self) -> None:
        handlers = restate_handlers.RestateHandlers(FakeActions())
        assert [sorted(d.handlers) for d in handlers.definitions()] == [["run"], ["quote"]]
