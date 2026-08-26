from __future__ import annotations

import beta.component.config as config


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = config.Spec(key="k")
        cfg = config.Config(spec)
        assert cfg.key == spec.key
