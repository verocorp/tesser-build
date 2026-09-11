from __future__ import annotations

import tesser.testing as ts
import pytest

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
        return ports.GetProductPriceResponse(
            outcome=ports.Priced.FOUND, prices=(ports.PriceRecord(cents=250),)
        )


@ts.fake
class FakeAbsurdProductCatalogRepository(ports.ProductCatalogRepository):

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        return ports.GetProductPriceResponse(
            outcome=ports.Priced.FOUND, prices=(ports.PriceRecord(cents=10**13),)
        )


@ts.fake
class FakeEmptyProductCatalogRepository(ports.ProductCatalogRepository):

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        return ports.GetProductPriceResponse(outcome=ports.Priced.MISSING, prices=())


class TestOrderActions:

    def test_pricing_a_product_answers_the_catalog_price(self) -> None:
        price_product_response = application.OrderActions(
            FakeProductCatalogRepository()
        ).price_product(relays.PriceProductRequest(sku="widget"))
        assert price_product_response.cents == 250

    def test_pricing_a_product_looks_the_sku_up_once(self) -> None:
        fake_product_catalog_repository = FakeProductCatalogRepository()
        application.OrderActions(fake_product_catalog_repository).price_product(
            relays.PriceProductRequest(sku="gadget")
        )
        assert fake_product_catalog_repository.priced == ["gadget"]

    def test_an_unknown_sku_is_the_engines_missing(self) -> None:
        with pytest.raises(ports.EngineMissing) as excinfo:
            application.OrderActions(FakeEmptyProductCatalogRepository()).price_product(
                relays.PriceProductRequest(sku="nothing")
            )
        assert excinfo.value.message == "no price for sku 'nothing'"

    def test_an_empty_sku_is_refused_before_the_catalog_is_asked(self) -> None:
        fake_product_catalog_repository = FakeProductCatalogRepository()
        with pytest.raises(ports.EngineRejected):
            application.OrderActions(fake_product_catalog_repository).price_product(
                relays.PriceProductRequest(sku="")
            )
        assert fake_product_catalog_repository.priced == []

    def test_a_catalog_price_past_the_bound_is_refused_before_it_crosses_the_engine(self) -> None:
        with pytest.raises(ports.EngineRejected) as excinfo:
            application.OrderActions(FakeAbsurdProductCatalogRepository()).price_product(
                relays.PriceProductRequest(sku="widget")
            )
        assert "at most" in excinfo.value.message
