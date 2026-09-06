from __future__ import annotations

import pytest

import ordering.adapters.repositories as repositories
import ordering.application.ports as ports
import tesser.errors as errors


class TestMemoryCatalogRepository:

    def test_a_known_sku_is_priced(self) -> None:
        memory_catalog_repository = repositories.MemoryCatalogRepository()
        price_response = memory_catalog_repository.price(ports.PriceRequest(sku="widget"))
        assert price_response.cents == 250

    def test_an_unknown_sku_is_not_found(self) -> None:
        memory_catalog_repository = repositories.MemoryCatalogRepository()
        with pytest.raises(errors.DomainError) as excinfo:
            memory_catalog_repository.price(ports.PriceRequest(sku="nothing"))
        assert excinfo.value.kind is errors.Kind.NOT_FOUND
