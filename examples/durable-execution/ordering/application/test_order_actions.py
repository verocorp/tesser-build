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
        return ports.GetProductPriceResponse(cents=250)


@ts.fake
class FakeAbsurdProductCatalogRepository(ports.ProductCatalogRepository):

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        return ports.GetProductPriceResponse(cents=10**13)


@ts.fake
class FakeEmptyProductCatalogRepository(ports.ProductCatalogRepository):

    def get_product_price(
        self, get_product_price_request: ports.GetProductPriceRequest
    ) -> ports.GetProductPriceResponse:
        raise errors.not_found(
            "unknown_sku", f"no price for sku {get_product_price_request.sku!r}"
        )


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

    def test_an_unknown_sku_is_the_catalogs_not_found(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            application.OrderActions(FakeEmptyProductCatalogRepository()).price_product(
                relays.PriceProductRequest(sku="nothing")
            )
        assert excinfo.value.kind is errors.Kind.NOT_FOUND

    def test_an_empty_sku_is_refused_before_the_catalog_is_asked(self) -> None:
        fake_product_catalog_repository = FakeProductCatalogRepository()
        with pytest.raises(errors.DomainError):
            application.OrderActions(fake_product_catalog_repository).price_product(
                relays.PriceProductRequest(sku="")
            )
        assert fake_product_catalog_repository.priced == []

    def test_a_catalog_price_past_the_bound_is_refused_before_it_crosses_the_engine(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            application.OrderActions(FakeAbsurdProductCatalogRepository()).price_product(
                relays.PriceProductRequest(sku="widget")
            )
        assert excinfo.value.code == "price_above_maximum"
