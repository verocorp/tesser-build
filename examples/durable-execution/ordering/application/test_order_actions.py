from __future__ import annotations

import tesser.testing as ts
import pytest

import ordering.application as application
import ordering.application.ports as ports
import ordering.application.relays as relays
import tesser.errors as errors


@ts.fake
class FakeProductCatalogRepository(ports.ProductCatalogRepository):

    def __init__(self) -> None:
        self.priced: list[str] = []

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        self.priced.append(get_product_price_request.sku)
        return ports.GetProductPriceResponse(
            outcome=ports.GetProductPriceOutcome.FOUND, prices=(ports.Price(cents=250),)
        )


@ts.fake
class FakeEmptyProductCatalogRepository(ports.ProductCatalogRepository):

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        return ports.GetProductPriceResponse(
            outcome=ports.GetProductPriceOutcome.NOT_FOUND, prices=()
        )


class TestOrderActions:

    def test_pricing_a_product_answers_the_catalog_price(self) -> None:
        price_product_response = application.OrderActions(
            FakeProductCatalogRepository()
        ).price_product(relays.PriceProductRequest(sku="widget"))
        assert price_product_response.outcome is relays.PriceProductOutcome.PRICED
        assert price_product_response.prices[0].cents == 250
        assert price_product_response.reasons == ()

    def test_pricing_a_product_looks_the_sku_up_once(self) -> None:
        fake_product_catalog_repository = FakeProductCatalogRepository()
        application.OrderActions(fake_product_catalog_repository).price_product(
            relays.PriceProductRequest(sku="gadget")
        )
        assert fake_product_catalog_repository.priced == ["gadget"]

    def test_an_unknown_sku_carries_the_catalogs_word_forward_as_a_price_not_found(self) -> None:
        price_product_response = application.OrderActions(
            FakeEmptyProductCatalogRepository()
        ).price_product(relays.PriceProductRequest(sku="nothing"))
        assert price_product_response.outcome is relays.PriceProductOutcome.PRICE_NOT_FOUND
        assert price_product_response.prices == ()
        assert price_product_response.reasons == ("no price for sku 'nothing'",)

    def test_an_empty_sku_is_a_fault_and_the_catalog_is_never_asked(self) -> None:
        fake_product_catalog_repository = FakeProductCatalogRepository()
        with pytest.raises(errors.DomainError):
            application.OrderActions(fake_product_catalog_repository).price_product(
                relays.PriceProductRequest(sku="")
            )
        assert fake_product_catalog_repository.priced == []
