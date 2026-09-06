from __future__ import annotations

import tesser.adapters as ts

import beta.application.ports as ports
import memoryclient.client as memoryclient


class MapToHasKeyResponse(ts.Mapper, ports.HasKeyResponse):

    def __init__(self, result: bool) -> None:
        super().__init__(held=ports.Held.YES if result else ports.Held.NO)


class MemoryKeyRepository(ts.Repository):

    def __init__(self) -> None:
        self._memory_client = memoryclient.MemoryClient()

    def has(self, has_key_request: ports.HasKeyRequest) -> ports.HasKeyResponse:
        result = self._memory_client.exists(has_key_request.key)
        return MapToHasKeyResponse(result)

    def close(self) -> None:
        return None
