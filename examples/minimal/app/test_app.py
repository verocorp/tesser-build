from __future__ import annotations

import alpha.client.client as alpha_client
import alpha.component.config as alpha_config
import app.app as app
import app.config as config
import beta.component.config as beta_config


def test_the_app_wires_alpha_through_beta() -> None:
    built = app.App(
        config.Config(
            config.Spec(
                alpha=alpha_config.Config(alpha_config.Spec(storage="memory")),
                beta=beta_config.Config(beta_config.Spec(key="a")),
            )
        )
    )
    assert built.alpha.client.add(alpha_client.AddRequest(name="a")).name == "a"
    built.close()
