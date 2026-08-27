from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application.order_orchestrator as order_orchestrator
import ordering.application.ports.quotes as quotes
import ordering.client.client as client


@ts.fake
class FakeQuotes(quotes.Quotes):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    async def quote(self, request: quotes.QuoteRequest) -> quotes.QuoteResponse:
        self.quoted.append(request.sku)
        return quotes.QuoteResponse(cents=250)


@ts.helper
def run_request(order_id: str = "o1", sku: str = "widget", quantity: int = 3) -> client.RunRequest:
    return client.RunRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderOrchestrator:

    def test_running_totals_the_quoted_price_over_the_quantity(self) -> None:
        orchestrator = order_orchestrator.OrderOrchestrator(FakeQuotes())
        ran = asyncio.run(orchestrator.run(run_request()))
        assert ran.order_id == "o1"
        assert ran.total_cents == 750

    def test_running_quotes_the_ordered_sku(self) -> None:
        fake_quotes = FakeQuotes()
        asyncio.run(order_orchestrator.OrderOrchestrator(fake_quotes).run(run_request(sku="gadget")))
        assert fake_quotes.quoted == ["gadget"]
