from __future__ import annotations

import app.config as config
import repo.component.config as repo_config


def test_a_config_carries_the_slice_its_component_reads() -> None:
    slice_ = repo_config.Config(repo_config.Spec())

    assert config.Config(config.Spec(repo=slice_)).repo is slice_
