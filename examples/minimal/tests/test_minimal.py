from __future__ import annotations

import alpha.client as alpha_client
import alpha.component as alpha_component
import app
import beta.component as beta_component


class TestWiredApp:

    def test_a_real_alpha_reaches_a_real_beta(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        assert minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="a", part="p")).name == "a"

    def test_a_widget_beta_holds_a_key_for_stands_as_kept(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        add_part_response = minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="k", part="k"))
        assert add_part_response.standing == "kept"

    def test_a_widget_beta_holds_no_key_for_stands_as_released(self) -> None:
        spec = app.Spec(alpha_component.Config(alpha_component.Spec("memory")), beta_component.Config(beta_component.Spec("a")))
        minimal_app = app.MinimalApp(app.AppConfig(spec))
        add_part_response = minimal_app.alpha.client.add_part(alpha_client.AddPartRequest(name="z", part="z"))
        assert add_part_response.standing == "released"
