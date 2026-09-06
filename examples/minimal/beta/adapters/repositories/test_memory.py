from __future__ import annotations

import beta.adapters.repositories as repositories
import beta.application.ports as ports


class TestMemoryKeyRepository:

    def test_the_stored_key_is_held(self) -> None:
        memory_key_repository = repositories.MemoryKeyRepository()
        has_key_response = memory_key_repository.has(ports.HasKeyRequest(key="k"))
        assert has_key_response.held is ports.Held.YES
