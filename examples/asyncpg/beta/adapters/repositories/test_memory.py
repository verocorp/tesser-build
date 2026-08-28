from __future__ import annotations

import beta.adapters.repositories.memory as memory
import beta.application.ports.key_repository as key_repository


class TestMemoryKeyRepository:

    async def test_a_put_key_is_held(self) -> None:
        keys = memory.MemoryKeyRepository()
        await keys.put(key_repository.PutKeyRequest(key="k"))
        answer = await keys.has(key_repository.HasKeyRequest(key="k"))
        assert answer.held is key_repository.Held.YES

    async def test_an_unknown_key_is_not_held(self) -> None:
        keys = memory.MemoryKeyRepository()
        answer = await keys.has(key_repository.HasKeyRequest(key="x"))
        assert answer.held is key_repository.Held.NO
