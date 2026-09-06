from __future__ import annotations

import tesser.application as ts

import beta.application.ports as ports
import beta.client as client
import beta.domain as domain


class MapToHasKeyRequest(ts.Mapper, ports.HasKeyRequest):

    def __init__(self, key: domain.Key) -> None:
        super().__init__(key=str(key))


class BetaService(ts.ApplicationService):

    def __init__(self, key_repository: ports.KeyRepository) -> None:
        self._key_repository = key_repository

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        key = domain.Key(check_request.key)
        has_key_response = self._key_repository.has(MapToHasKeyRequest(key))
        return client.CheckResponse(held=has_key_response.held.value)
