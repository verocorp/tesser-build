from __future__ import annotations

import pytest

import ordering.adapters.repositories as repositories
import ordering.application.ports as ports
import tesser.errors as errors


class TestMemoryProductCatalogRepository:

    def test_a_known_sku_is_priced(self) -> None:
        get_product_price_response = repositories.MemoryProductCatalogRepository().get_product_price(
            ports.GetProductPriceRequest(sku="widget")
        )
        assert get_product_price_response.cents == 250

    def test_an_unknown_sku_is_not_found(self) -> None:
        with pytest.raises(errors.DomainError) as excinfo:
            repositories.MemoryProductCatalogRepository().get_product_price(
                ports.GetProductPriceRequest(sku="nothing")
            )
        assert excinfo.value.kind is errors.Kind.NOT_FOUND
