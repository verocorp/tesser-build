from __future__ import annotations

import linkpolicy.component.config as config


def test_a_config_carries_the_storage_coordinate_it_was_given() -> None:
    assert config.Config(config.Spec("memory")).storage == "memory"


def test_a_config_carries_the_storage_coordinate_given_by_name() -> None:
    assert config.Config(config.Spec(storage="memory")).storage == "memory"


def test_a_config_accepts_an_absent_storage_coordinate() -> None:
    assert config.Config(config.Spec("")).storage == ""
