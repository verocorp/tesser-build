from __future__ import annotations

import asyncio

import pytest

import ordering.adapters.repositories.memory as memory
import ordering.application.ports.catalog_repository as catalog_repository
import tesser.errors as errors


class TestMemoryCatalogRepository:

    def test_a_known_sku_is_priced(self) -> None:
        catalog = memory.MemoryCatalogRepository()
        priced = asyncio.run(catalog.price(catalog_repository.PriceRequest(sku="widget")))
        assert priced.cents == 250

    def test_an_unknown_sku_is_not_found(self) -> None:
        catalog = memory.MemoryCatalogRepository()
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(catalog.price(catalog_repository.PriceRequest(sku="nothing")))
        assert excinfo.value.kind is errors.Kind.NOT_FOUND
