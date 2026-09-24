from __future__ import annotations

import tesser.adapters as ts

import beta.application.ports as ports


class MapToHasKeyResponse(ts.Mapper, ports.HasKeyResponse):

    def __init__(self, result: bool) -> None:
        super().__init__(outcome=ports.HasKeyOutcome.YES if result else ports.HasKeyOutcome.NO)


class MemoryKeyRepository(ts.Repository):

    def __init__(self) -> None:
        self._keys = frozenset({"k"})

    def has_key(self, has_key_request: ports.HasKeyRequest) -> ports.HasKeyResponse:
        result = has_key_request.key in self._keys
        return MapToHasKeyResponse(result)

    def close(self) -> None:
        return None
