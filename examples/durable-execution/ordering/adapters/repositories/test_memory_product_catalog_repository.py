from __future__ import annotations

import ordering.adapters.repositories as repositories
import ordering.application.ports as ports


class TestMemoryProductCatalogRepository:

    def test_a_known_sku_is_priced(self) -> None:
        get_product_price_response = repositories.MemoryProductCatalogRepository().get_product_price(
            ports.GetProductPriceRequest(sku="widget")
        )
        assert get_product_price_response.outcome is ports.Priced.FOUND
        assert get_product_price_response.prices[0].cents == 250

    def test_an_unknown_sku_is_missing(self) -> None:
        get_product_price_response = repositories.MemoryProductCatalogRepository().get_product_price(
            ports.GetProductPriceRequest(sku="nothing")
        )
        assert get_product_price_response.outcome is ports.Priced.MISSING
        assert get_product_price_response.prices == ()

    def test_a_closed_catalog_prices_nothing(self) -> None:
        memory_product_catalog_repository = repositories.MemoryProductCatalogRepository()
        memory_product_catalog_repository.close()
        get_product_price_response = memory_product_catalog_repository.get_product_price(
            ports.GetProductPriceRequest(sku="widget")
        )
        assert get_product_price_response.outcome is ports.Priced.MISSING
