from __future__ import annotations

import alpha.client.client as alpha_client
import alpha.component.config as alpha_config
import app.app as app
import app.config as config
import beta.component.config as beta_config


class TestWiredApp:

    def test_a_real_alpha_reaches_a_real_beta(self) -> None:
        spec = config.Spec(alpha_config.Config(alpha_config.Spec("memory")), beta_config.Config(beta_config.Spec("a")))
        built = app.App(config.Config(spec))
        assert built.alpha.client.add(alpha_client.AddRequest(name="a")).name == "a"
