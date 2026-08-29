from __future__ import annotations

import app.config as config
import ordering.component.config as ordering_config


class TestConfig:

    def test_a_config_carries_the_component_config(self) -> None:
        spec = config.Spec(ordering_config.Config(ordering_config.Spec("http://localhost:8080")))
        cfg = config.Config(spec)
        assert cfg.ordering is spec.ordering
