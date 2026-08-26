from __future__ import annotations

import alpha.component.config as alpha_config
import app.app as app
import app.config as config
import beta.component.config as beta_config


def test_the_app_wires_and_closes() -> None:
    spec = config.Spec(alpha_config.Config(alpha_config.Spec("memory")), beta_config.Config(beta_config.Spec("a")))
    app.App(config.Config(spec)).close()
