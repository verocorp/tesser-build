from __future__ import annotations

import alpha.component.config as alpha_config
import app.config as config
import beta.component.config as beta_config


class TestConfig:

    def test_a_config_carries_each_component_config(self) -> None:
        spec = config.Spec(
            alpha_config.Config(alpha_config.Spec("postgres://a@b/alpha")),
            beta_config.Config(beta_config.Spec("postgres://a@b/beta")),
        )
        cfg = config.Config(spec)
        assert cfg.beta is spec.beta
