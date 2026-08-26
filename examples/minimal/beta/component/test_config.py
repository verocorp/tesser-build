from __future__ import annotations

import beta.component.config as config


def test_a_config_carries_its_spec() -> None:
    assert config.Config(config.Spec(keys=("k",))).keys == ("k",)
