from __future__ import annotations

import app.config as config
import app.repository as repository


def test_the_env_repository_reads_the_environment_the_runner_supplied() -> None:
    cfg = repository.EnvConfigRepository().get()

    assert isinstance(cfg, config.Config)
    assert cfg.campaign.storage == "memory"
    assert cfg.linkpolicy.storage == "memory"


def test_each_read_returns_its_own_config() -> None:
    reader = repository.EnvConfigRepository()

    assert reader.get() is not reader.get()
