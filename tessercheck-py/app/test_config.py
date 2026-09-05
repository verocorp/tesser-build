from __future__ import annotations

import app.config as config
import tessercheck.component as component


def test_a_config_carries_the_slice_its_component_reads() -> None:
    slice_ = component.Config(component.Spec())

    cfg = config.Config(config.Spec(tessercheck=slice_))

    assert cfg.tessercheck is slice_


def test_each_config_carries_its_own_slice() -> None:
    first = config.Config(
        config.Spec(tessercheck=component.Config(component.Spec()))
    )
    second = config.Config(
        config.Spec(tessercheck=component.Config(component.Spec()))
    )

    assert first.tessercheck is not second.tessercheck
