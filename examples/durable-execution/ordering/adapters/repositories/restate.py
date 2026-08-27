from __future__ import annotations

import collections.abc as abc
import json

import tesser.adapters as ts

import ordering.application.ports.catalog_repository as catalog_repository
import tesser.errors as errors


class RestateCatalogRepository(ts.Repository):

    def __init__(
        self,
        inner: catalog_repository.CatalogRepository,
        run: abc.Callable[[str, abc.Callable[[], abc.Coroutine[object, object, bytes]]], abc.Awaitable[bytes]],
    ) -> None:
        self._inner = inner
        self._run = run

    async def price(self, request: catalog_repository.PriceRequest) -> catalog_repository.PriceResponse:
        inner = self._inner

        async def action() -> bytes:
            try:
                priced = await inner.price(request)
            except errors.DomainError as e:
                return json.dumps({"error": {"kind": e.kind.value, "code": e.code, "message": e.message}}).encode()
            return json.dumps({"cents": priced.cents}).encode()

        data = json.loads(await self._run("price", action))
        if not isinstance(data, dict):
            raise errors.InfraError("the journaled price is not a JSON object")
        error = data.get("error")
        if isinstance(error, dict):
            raise errors.DomainError(errors.Kind(error["kind"]), str(error["code"]), str(error["message"]))
        cents = data.get("cents")
        if isinstance(cents, bool) or not isinstance(cents, int):
            raise errors.InfraError("the journaled price carries no integer cents")
        return catalog_repository.PriceResponse(cents=cents)
