from __future__ import annotations

import asyncio
import collections.abc as abc

import pytest
import tesser.testing as ts

import ordering.adapters.repositories.restate as restate_repository
import ordering.application.ports.catalog_repository as catalog_repository
import tesser.errors as errors


@ts.fake
class FakeCatalogRepository(catalog_repository.CatalogRepository):

    def __init__(self) -> None:
        self.calls = 0

    async def price(self, request: catalog_repository.PriceRequest) -> catalog_repository.PriceResponse:
        self.calls += 1
        if request.sku == "nothing":
            raise errors.not_found("unknown_sku", "no price")
        return catalog_repository.PriceResponse(cents=250)


class TestRestateCatalogRepository:

    def test_a_price_is_run_as_a_named_journaled_step(self) -> None:
        names: list[str] = []

        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            names.append(name)
            return await action()

        catalog = restate_repository.RestateCatalogRepository(FakeCatalogRepository(), run)
        priced = asyncio.run(catalog.price(catalog_repository.PriceRequest(sku="widget")))
        assert priced.cents == 250
        assert names == ["price"]

    def test_a_replayed_step_answers_from_the_journal_without_the_inner_call(self) -> None:
        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            return b'{"cents": 999}'

        inner = FakeCatalogRepository()
        catalog = restate_repository.RestateCatalogRepository(inner, run)
        priced = asyncio.run(catalog.price(catalog_repository.PriceRequest(sku="widget")))
        assert priced.cents == 999
        assert inner.calls == 0

    def test_a_domain_error_is_journaled_as_a_result_and_raised_again(self) -> None:
        journal: list[bytes] = []

        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            journal.append(await action())
            return journal[-1]

        catalog = restate_repository.RestateCatalogRepository(FakeCatalogRepository(), run)
        with pytest.raises(errors.DomainError) as excinfo:
            asyncio.run(catalog.price(catalog_repository.PriceRequest(sku="nothing")))
        assert excinfo.value.kind is errors.Kind.NOT_FOUND
        assert excinfo.value.code == "unknown_sku"
        assert b'"error"' in journal[0]

    def test_a_journal_entry_without_cents_is_an_infra_error(self) -> None:
        async def run(name: str, action: abc.Callable[[], abc.Coroutine[object, object, bytes]]) -> bytes:
            return b'{"cents": "250"}'

        catalog = restate_repository.RestateCatalogRepository(FakeCatalogRepository(), run)
        with pytest.raises(errors.InfraError):
            asyncio.run(catalog.price(catalog_repository.PriceRequest(sku="widget")))
