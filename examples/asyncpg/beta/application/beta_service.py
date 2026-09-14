from __future__ import annotations

import tesser.application as ts

import beta.application.ports as ports
import beta.client as client
import beta.domain as domain
import tesser.errors as errors


class MapToHasKeyRequest(ts.Mapper, ports.HasKeyRequest):

    def __init__(self, key: domain.Key) -> None:
        super().__init__(key=str(key))


class MapToPutKeyRequest(ts.Mapper, ports.PutKeyRequest):

    def __init__(self, key: domain.Key) -> None:
        super().__init__(key=str(key))


class BetaService(ts.ApplicationService):

    def __init__(self, key_store: ports.KeyStore) -> None:
        self._key_store = key_store

    async def check_key(self, check_key_request: client.CheckKeyRequest) -> client.CheckKeyResponse:
        try:
            key = domain.Key(check_key_request.key)
        except errors.DomainError as domain_error:
            raise client.KeyRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        async with self._key_store.transaction() as key_repository:
            has_key_response = await key_repository.has_key(MapToHasKeyRequest(key))
        return client.CheckKeyResponse(held=has_key_response.outcome.value)

    async def hold_key(self, hold_key_request: client.HoldKeyRequest) -> client.HoldKeyResponse:
        try:
            key = domain.Key(hold_key_request.key)
        except errors.DomainError as domain_error:
            raise client.KeyRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        async with self._key_store.transaction() as key_repository:
            put_key_response = await key_repository.put_key(MapToPutKeyRequest(key))
        return client.HoldKeyResponse(key=put_key_response.key)
