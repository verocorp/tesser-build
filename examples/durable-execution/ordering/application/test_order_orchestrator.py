from __future__ import annotations

import asyncio

import tesser.testing as ts

import ordering.application.order_orchestrator as order_orchestrator
import ordering.application.ports.catalog_repository as catalog_repository
import ordering.client.client as client


@ts.fake
class FakeCatalogRepository(catalog_repository.CatalogRepository):

    def __init__(self) -> None:
        self.priced: list[str] = []

    async def price(self, request: catalog_repository.PriceRequest) -> catalog_repository.PriceResponse:
        self.priced.append(request.sku)
        return catalog_repository.PriceResponse(cents=250)


@ts.helper
def run_request(order_id: str = "o1", sku: str = "widget", quantity: int = 3) -> client.RunRequest:
    return client.RunRequest(order_id=order_id, sku=sku, quantity=quantity)


class TestOrderOrchestrator:

    def test_running_totals_the_unit_price_over_the_quantity(self) -> None:
        orchestrator = order_orchestrator.OrderOrchestrator(FakeCatalogRepository())
        ran = asyncio.run(orchestrator.run(run_request()))
        assert ran.order_id == "o1"
        assert ran.total_cents == 750

    def test_running_prices_the_ordered_sku(self) -> None:
        catalog = FakeCatalogRepository()
        asyncio.run(order_orchestrator.OrderOrchestrator(catalog).run(run_request(sku="gadget")))
        assert catalog.priced == ["gadget"]
