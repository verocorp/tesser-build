from __future__ import annotations

import repo.component.config as config


def test_a_config_constructs_from_its_spec() -> None:
    assert isinstance(config.Config(config.Spec()), config.Config)


def test_each_config_is_its_own() -> None:
    assert config.Config(config.Spec()) is not config.Config(config.Spec())
