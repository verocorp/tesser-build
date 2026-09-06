from __future__ import annotations

import tesser.testing as ts

import ordering.application as application
import ordering.application.ports as ports
import ordering.application.relays as relays


@ts.fake
class FakeProductCatalogRepository(ports.ProductCatalogRepository):

    def __init__(self) -> None:
        self.priced: list[str] = []

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        self.priced.append(get_product_price_request.sku)
        return ports.GetProductPriceResponse(cents=250)


class TestOrderActions:

    def test_preparing_a_quote_answers_the_catalog_price(self) -> None:
        prepare_quote_response = application.OrderActions(
            FakeProductCatalogRepository()
        ).prepare_quote(relays.PrepareQuoteRequest(sku="widget"))
        assert prepare_quote_response.cents == 250

    def test_preparing_a_quote_looks_the_sku_up_once(self) -> None:
        fake_product_catalog_repository = FakeProductCatalogRepository()
        application.OrderActions(fake_product_catalog_repository).prepare_quote(
            relays.PrepareQuoteRequest(sku="gadget")
        )
        assert fake_product_catalog_repository.priced == ["gadget"]
