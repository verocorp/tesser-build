from __future__ import annotations

import ordering.component.config as config


class TestConfig:

    def test_a_config_carries_its_spec(self) -> None:
        spec = config.Spec(ingress="http://localhost:8080")
        cfg = config.Config(spec)
        assert cfg.ingress == spec.ingress
