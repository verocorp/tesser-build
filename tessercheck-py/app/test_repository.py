from __future__ import annotations

import app.config as config
import app.repository as repository


def test_the_env_repository_reads_a_config() -> None:
    assert isinstance(repository.EnvConfigRepository().get(), config.AppConfig)


def test_each_read_returns_its_own_config() -> None:
    env_config_repository = repository.EnvConfigRepository()

    assert env_config_repository.get() is not env_config_repository.get()
