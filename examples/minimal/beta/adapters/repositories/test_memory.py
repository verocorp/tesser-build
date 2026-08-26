from __future__ import annotations

import beta.adapters.repositories.memory as memory
import beta.application.ports.key_repository as key_repository


class TestMemoryKeyRepository:

    def test_the_stored_key_is_held(self) -> None:
        keys = memory.MemoryKeyRepository()
        answer = keys.has(key_repository.HasKeyRequest(key="k"))
        assert answer.held is key_repository.Held.YES
