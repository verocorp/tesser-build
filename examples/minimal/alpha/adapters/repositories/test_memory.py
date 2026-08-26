from __future__ import annotations

import alpha.adapters.repositories.memory as memory
import alpha.application.ports.thing_repository as thing_repository


def test_a_save_is_answered() -> None:
    memory.MemoryThingRepository().save(thing_repository.SaveRequest(name="a"))
