from __future__ import annotations

import beta.adapters.repositories.memory as memory
import beta.application.ports.key_store as key_store


def test_a_held_key_answers_yes() -> None:
    store = memory.MemoryKeyStore(keys=("k",))
    assert store.has(key_store.HasKeyRequest(key="k")).held is key_store.Held.YES
    assert store.has(key_store.HasKeyRequest(key="x")).held is key_store.Held.NO
