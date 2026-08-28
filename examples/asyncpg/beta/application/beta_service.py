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

    def __init__(self, keys: key_repository.KeyRepository) -> None:
        self._keys = keys

    async def check(self, request: client.CheckRequest) -> client.CheckResponse:
        checked_key = key.Key(request.key)
        answer = await self._keys.has(MapToHasKeyRequest(checked_key))
        return client.CheckResponse(held=answer.held.value)

    async def hold(self, request: client.HoldRequest) -> client.HoldResponse:
        held_key = key.Key(request.key)
        put = await self._keys.put(MapToPutKeyRequest(held_key))
        return client.HoldResponse(key=put.key)
