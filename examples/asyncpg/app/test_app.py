from __future__ import annotations

import alpha.client.client as alpha_client
import alpha.component.config as alpha_config
import app.app as app
import app.config as config
import beta.component.config as beta_config


class TestApp:

    async def test_the_app_wires_alpha_through_beta(self) -> None:
        spec = config.Spec(alpha_config.Config(alpha_config.Spec("memory")), beta_config.Config(beta_config.Spec("memory")))
        built = app.App(config.Config(spec))
        added = await built.alpha.client.add(alpha_client.AddRequest(name="a", part="p"))
        await built.close()
        assert added.name == "a"
