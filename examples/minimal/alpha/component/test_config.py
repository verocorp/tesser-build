from __future__ import annotations

import alpha.component.config as config


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = config.Spec(storage="memory")
        component_config = config.Config(spec)
        assert component_config.storage == spec.storage
