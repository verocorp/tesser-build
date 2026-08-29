from __future__ import annotations

import tesser.testing as ts

import ordering.application.order_actions as actions
import ordering.application.ports.catalog_repository as catalog_repository
import ordering.application.ports.order_actions as order_actions


@ts.fake
class FakeCatalogRepository(catalog_repository.CatalogRepository):

    def __init__(self) -> None:
        self.priced: list[str] = []

    def price(self, request: catalog_repository.PriceRequest) -> catalog_repository.PriceResponse:
        self.priced.append(request.sku)
        return catalog_repository.PriceResponse(cents=250)


class TestOrderActions:

    def test_quoting_answers_the_catalog_price(self) -> None:
        quoted = actions.OrderActions(FakeCatalogRepository()).quote(
            order_actions.QuoteRequest(sku="widget")
        )
        assert quoted.cents == 250

    def test_quoting_looks_the_sku_up_once(self) -> None:
        catalog = FakeCatalogRepository()
        actions.OrderActions(catalog).quote(order_actions.QuoteRequest(sku="gadget"))
        assert catalog.priced == ["gadget"]
