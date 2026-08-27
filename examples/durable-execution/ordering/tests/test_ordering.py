from __future__ import annotations

import json

import ordering.adapters.handlers.restate as restate_handlers
import ordering.component.component as component
import ordering.component.config as config
import protocol.durable as durable


class TestOrderingContext:

    def test_the_action_handler_quotes_through_the_wired_actions(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        handler = restate_handlers.ActionHandler(wired.actions)
        response = handler.quote(durable.ActionRequest(body=b'{"sku": "gadget"}'))
        assert json.loads(response.body) == {"cents": 1000}
