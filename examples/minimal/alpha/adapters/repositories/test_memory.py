from __future__ import annotations

import alpha.adapters.repositories.memory as memory
import alpha.application.ports.thing_repository as thing_repository


def test_a_save_answers_the_saved_name() -> None:
    assert memory.MemoryThingRepository().save(thing_repository.SaveRequest(name="a")).name == "a"
