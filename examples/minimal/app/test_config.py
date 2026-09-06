from __future__ import annotations

import alpha.component as alpha_component
import app.config as config
import beta.component as beta_component


class TestConfig:

    def test_a_config_carries_each_component_config(self) -> None:
        spec = config.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("k")))
        app_config = config.AppConfig(spec)
        assert app_config.beta is spec.beta
