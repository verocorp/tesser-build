from __future__ import annotations

import tesser.application as ts

import beta.application.ports.key_repository as key_repository
import beta.client.client as client
import beta.domain.key as key


class MapToHasKeyRequest(ts.Mapper, key_repository.HasKeyRequest):

    def __init__(self, checked_key: key.Key) -> None:
        super().__init__(key=str(checked_key))


class MapToPutKeyRequest(ts.Mapper, key_repository.PutKeyRequest):

    def __init__(self, held_key: key.Key) -> None:
        super().__init__(key=str(held_key))


class BetaService(ts.ApplicationService):

    def __init__(self, key_store: key_repository.KeyStore) -> None:
        self._key_store = key_store

    async def check(self, request: client.CheckRequest) -> client.CheckResponse:
        checked_key = key.Key(request.key)
        async with self._key_store.transaction() as keys:
            answer = await keys.has_key(MapToHasKeyRequest(checked_key))
        return client.CheckResponse(held=answer.held.value)

    async def hold(self, request: client.HoldRequest) -> client.HoldResponse:
        held_key = key.Key(request.key)
        async with self._key_store.transaction() as keys:
            put = await keys.put_key(MapToPutKeyRequest(held_key))
        return client.HoldResponse(key=put.key)
