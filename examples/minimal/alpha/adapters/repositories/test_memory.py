from __future__ import annotations

import pytest

import alpha.adapters.repositories.memory as memory
import alpha.application.ports.whole_repository as whole_repository
import tesser.errors as errors


def test_a_saved_whole_is_found() -> None:
    repo = memory.MemoryWholeRepository()
    repo.save(whole_repository.SaveWholeRequest(id="w", name="a", count=1))
    found = repo.find(whole_repository.FindWholeRequest(id="w"))
    assert found.outcome is whole_repository.Lookup.PRESENT


def test_a_closed_repository_refuses_a_save() -> None:
    repo = memory.MemoryWholeRepository()
    repo.close()
    with pytest.raises(errors.InfraError):
        repo.save(whole_repository.SaveWholeRequest(id="w", name="a", count=1))
