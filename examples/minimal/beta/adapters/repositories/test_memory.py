from __future__ import annotations

import beta.adapters.repositories.memory as memory
import beta.application.ports.key_store as key_store


def test_only_the_configured_key_is_held() -> None:
    store = memory.MemoryKeyStore(key="k")
    assert store.has(key_store.HasKeyRequest(key="k")).held is key_store.Held.YES
    assert store.has(key_store.HasKeyRequest(key="x")).held is key_store.Held.NO
