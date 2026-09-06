from __future__ import annotations

import tesser.application as ts

import beta.application.ports as ports
import beta.client as client
import beta.domain as domain


class MapToHasKeyRequest(ts.Mapper, ports.HasKeyRequest):

    def __init__(self, key: domain.Key) -> None:
        super().__init__(key=str(key))


class MapToPutKeyRequest(ts.Mapper, ports.PutKeyRequest):

    def __init__(self, key: domain.Key) -> None:
        super().__init__(key=str(key))


class BetaService(ts.ApplicationService):

    def __init__(self, key_store: ports.KeyStore) -> None:
        self._key_store = key_store

    async def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        key = domain.Key(check_request.key)
        async with self._key_store.transaction() as key_repository:
            has_key_response = await key_repository.has_key(MapToHasKeyRequest(key))
        return client.CheckResponse(held=has_key_response.held.value)

    async def hold(self, hold_request: client.HoldRequest) -> client.HoldResponse:
        key = domain.Key(hold_request.key)
        async with self._key_store.transaction() as key_repository:
            put_key_response = await key_repository.put_key(MapToPutKeyRequest(key))
        return client.HoldResponse(key=put_key_response.key)
