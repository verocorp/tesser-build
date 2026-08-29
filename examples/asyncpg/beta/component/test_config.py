from __future__ import annotations

import beta.component.config as config


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = config.Spec(storage="memory")
        cfg = config.Config(spec)
        assert cfg.storage == spec.storage
