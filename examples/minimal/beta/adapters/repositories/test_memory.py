from __future__ import annotations

import beta.adapters.repositories.memory as memory
import beta.application.ports.key_store as key_store


class TestMemoryKeyStore:

    def test_the_configured_key_is_held(self) -> None:
        keys = memory.MemoryKeyStore(key="k")
        answer = keys.has(key_store.HasKeyRequest(key="k"))
        assert answer.held is key_store.Held.YES
