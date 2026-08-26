from __future__ import annotations

import alpha.component.config as alpha_config
import app.config as config
import beta.component.config as beta_config


def test_a_config_carries_each_component_config() -> None:
    cfg = config.Config(
        config.Spec(
            alpha=alpha_config.Config(alpha_config.Spec(storage="memory")),
            beta=beta_config.Config(beta_config.Spec(key="k")),
        )
    )
    assert cfg.alpha.storage == "memory"
    assert cfg.beta.key == "k"
