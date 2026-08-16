from __future__ import annotations

import bootstrap.config as config
import bootstrap.repository as repository


def test_the_env_repository_reads_a_config() -> None:
    assert isinstance(repository.EnvConfigRepository().get(), config.Config)


def test_each_read_returns_its_own_config() -> None:
    reader = repository.EnvConfigRepository()

    assert reader.get() is not reader.get()
