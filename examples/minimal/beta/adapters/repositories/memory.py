from __future__ import annotations

import tesser.adapters as ts

import beta.application.ports.key_repository as key_repository
import memoryclient.client as memoryclient
import tesser.application as application  # tesser:debt TB050


class MapToHasKeyResponse(application.Mapper, key_repository.HasKeyResponse):  # tesser:debt TB052

    def __init__(self, result: bool) -> None:  # tesser:debt TB080
        super().__init__(held=key_repository.Held.YES if result else key_repository.Held.NO)


class MemoryKeyRepository(ts.Repository):

    def __init__(self) -> None:
        self._memory_client = memoryclient.MemoryClient()

    def has(self, request: key_repository.HasKeyRequest) -> key_repository.HasKeyResponse:
        result = self._memory_client.exists(request.key)
        return MapToHasKeyResponse(result)

    def close(self) -> None:
        return None
