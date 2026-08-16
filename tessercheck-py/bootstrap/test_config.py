from __future__ import annotations

import bootstrap.config as config
import tessercheck.wiring.config as component_config


def test_a_config_carries_the_slice_its_component_reads() -> None:
    slice_ = component_config.Config(component_config.Spec())

    cfg = config.Config(config.Spec(tessercheck=slice_))

    assert cfg.tessercheck is slice_


def test_each_config_carries_its_own_slice() -> None:
    first = config.Config(
        config.Spec(tessercheck=component_config.Config(component_config.Spec()))
    )
    second = config.Config(
        config.Spec(tessercheck=component_config.Config(component_config.Spec()))
    )

    assert first.tessercheck is not second.tessercheck
