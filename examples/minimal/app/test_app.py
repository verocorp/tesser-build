from __future__ import annotations

import alpha.client as client
import alpha.component as alpha_component
import app.app as app
import app.config as config
import beta.component as beta_component


class TestApp:

    def test_the_app_wires_alpha_through_beta(self) -> None:
        spec = config.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        app_app = app.App(config.Config(spec))
        assert app_app.alpha.client.add(client.AddRequest(name="a", part="p")).name == "a"
