from __future__ import annotations

import beta.component.config as config


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = config.Spec(key="k")
        component_config = config.Config(spec)
        assert component_config.key == spec.key
