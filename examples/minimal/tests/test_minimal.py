from __future__ import annotations

import alpha.client as client
import alpha.component as alpha_component
import app.app as app
import app.config as config
import beta.component as beta_component


class TestWiredApp:

    def test_a_real_alpha_reaches_a_real_beta(self) -> None:
        spec = config.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(config.AppConfig(spec))
        assert minimal_app.alpha.client.add(client.AddRequest(name="a", part="p")).name == "a"

    def test_a_widget_beta_holds_a_key_for_stands_as_kept(self) -> None:
        spec = config.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(config.AppConfig(spec))
        added = minimal_app.alpha.client.add(client.AddRequest(name="k", part="k"))
        assert added.standing == "kept"

    def test_a_widget_beta_holds_no_key_for_stands_as_released(self) -> None:
        spec = config.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(config.AppConfig(spec))
        added = minimal_app.alpha.client.add(client.AddRequest(name="z", part="z"))
        assert added.standing == "released"
