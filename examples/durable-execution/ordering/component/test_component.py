from __future__ import annotations

import ordering.client.client as client
import ordering.component.component as component
import ordering.component.config as config


class TestOrdering:

    def test_the_wired_actions_quote_from_the_catalog(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        quoted = wired.actions.quote(client.QuoteRequest(sku="widget"))
        assert quoted.cents == 250

    def test_the_component_publishes_the_restate_address_it_wired_its_gateways_with(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        assert (wired.address.workflow, wired.address.run) == ("Ordering", "run")
        assert (wired.address.actions, wired.address.quote) == ("OrderingActions", "quote")
