from __future__ import annotations

import ordering.client.client as client
import ordering.component.component as component
import ordering.component.config as config


class TestOrdering:

    def test_the_wired_actions_quote_from_the_catalog(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        quoted = wired.actions.quote(client.QuoteRequest(sku="widget"))
        assert quoted.cents == 250
