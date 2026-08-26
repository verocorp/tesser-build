from __future__ import annotations

import pytest

import alpha.adapters.repositories.memory as memory
import alpha.application.ports.thing_repository as thing_repository
import tesser.errors as errors


def test_a_closed_repository_refuses_a_save() -> None:
    repo = memory.MemoryThingRepository()
    repo.close()
    with pytest.raises(errors.InfraError):
        repo.save(thing_repository.SaveRequest(name="a"))
