from __future__ import annotations

import app.app as app
import app.config as config
import ordering.client.client as ordering_client
import ordering.component.config as ordering_config


class TestWiredApp:

    def test_a_real_action_quotes_from_the_real_catalog(self) -> None:
        spec = config.Spec(ordering_config.Config(ordering_config.Spec("http://localhost:8080")))
        built = app.App(config.Config(spec))
        assert built.ordering.actions.quote(ordering_client.QuoteRequest(sku="widget")).cents == 250
