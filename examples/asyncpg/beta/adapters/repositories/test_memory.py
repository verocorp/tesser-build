from __future__ import annotations

import pytest

import beta.adapters.repositories.memory as memory
import beta.application.ports.key_repository as key_repository


class TestMemoryKeyStore:

    async def test_a_put_key_is_held_in_a_later_transaction(self) -> None:
        key_store = memory.MemoryKeyStore()
        async with key_store.transaction() as keys:
            await keys.put_key(key_repository.PutKeyRequest(key="k"))
        async with key_store.transaction() as keys:
            held = await keys.has_key(key_repository.HasKeyRequest(key="k"))
            missing = await keys.has_key(key_repository.HasKeyRequest(key="x"))
        assert held.held is key_repository.Held.YES
        assert missing.held is key_repository.Held.NO

    async def test_a_transaction_that_raises_restores_the_state_before_it(self) -> None:
        key_store = memory.MemoryKeyStore()
        with pytest.raises(RuntimeError):
            async with key_store.transaction() as keys:
                await keys.put_key(key_repository.PutKeyRequest(key="k"))
                raise RuntimeError("abort")
        async with key_store.transaction() as keys:
            missing = await keys.has_key(key_repository.HasKeyRequest(key="k"))
        assert missing.held is key_repository.Held.NO
