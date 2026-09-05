from __future__ import annotations

import beta.adapters.repositories.memory as memory
import beta.application.ports as ports


class TestMemoryKeyRepository:

    def test_the_stored_key_is_held(self) -> None:
        memory_key_repository = memory.MemoryKeyRepository()
        answer = memory_key_repository.has(ports.HasKeyRequest(key="k"))
        assert answer.held is ports.Held.YES
