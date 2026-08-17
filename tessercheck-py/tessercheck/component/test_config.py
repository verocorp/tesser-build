from __future__ import annotations

import tessercheck.component.config as config
import tessercheck.component.component as wire


def test_a_config_constructs_from_its_spec() -> None:
    assert isinstance(config.Config(config.Spec()), config.Config)


def test_each_config_is_its_own() -> None:
    assert config.Config(config.Spec()) is not config.Config(config.Spec())


def test_a_component_takes_the_config_it_is_given() -> None:
    built = wire.Tessercheck(config.Config(config.Spec()))

    assert built.client is not None
