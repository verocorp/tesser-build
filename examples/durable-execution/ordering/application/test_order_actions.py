from __future__ import annotations

import tesser.testing as ts

import ordering.application as application
import ordering.application.ports as ports


@ts.fake
class FakeCatalogRepository(ports.CatalogRepository):

    def __init__(self) -> None:
        self.priced: list[str] = []

    def price(self, price_request: ports.PriceRequest) -> ports.PriceResponse:
        self.priced.append(price_request.sku)
        return ports.PriceResponse(cents=250)


class TestOrderActions:

    def test_quoting_answers_the_catalog_price(self) -> None:
        quote_response = application.OrderActions(FakeCatalogRepository()).quote(
            ports.QuoteRequest(sku="widget")
        )
        assert quote_response.cents == 250

    def test_quoting_looks_the_sku_up_once(self) -> None:
        fake_catalog_repository = FakeCatalogRepository()
        application.OrderActions(fake_catalog_repository).quote(ports.QuoteRequest(sku="gadget"))
        assert fake_catalog_repository.priced == ["gadget"]
