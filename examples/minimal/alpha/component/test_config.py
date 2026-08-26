from __future__ import annotations

import alpha.component.config as config


def test_a_config_carries_its_spec() -> None:
    assert config.Config(config.Spec(storage="memory")).storage == "memory"
