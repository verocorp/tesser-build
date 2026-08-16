from __future__ import annotations

import campaign.wiring.config as config


def test_the_config_carries_the_storage_coordinate_it_was_given() -> None:
    cfg = config.Config(storage="memory")

    assert cfg.storage == "memory"


def test_the_config_carries_an_unknown_coordinate_without_judging_it() -> None:
    cfg = config.Config(storage="postgres")

    assert cfg.storage == "postgres"


def test_the_config_carries_an_absent_coordinate_without_judging_it() -> None:
    cfg = config.Config(storage="")

    assert cfg.storage == ""


def test_two_configs_built_from_the_same_coordinate_are_separate_objects() -> None:
    first = config.Config(storage="memory")
    second = config.Config(storage="memory")

    assert first is not second
    assert first.storage == second.storage
