from __future__ import annotations

import alpha.component.config as alpha_config
import app.config as config
import beta.component.config as beta_config


def test_a_config_carries_each_component_config() -> None:
    spec = config.Spec(alpha_config.Config(alpha_config.Spec("memory")), beta_config.Config(beta_config.Spec("k")))
    assert config.Config(spec).beta.key == "k"
