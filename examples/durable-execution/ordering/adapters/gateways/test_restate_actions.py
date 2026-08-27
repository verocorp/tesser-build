from __future__ import annotations

import asyncio

import pytest

import ordering.adapters.gateways.restate_actions as restate_actions
import ordering.application.ports.order_actions as order_actions
import tesser.errors as errors


class TestRestateOrderActions:

    def test_a_quote_outside_an_invocation_is_an_infra_error(self) -> None:
        actions = restate_actions.RestateOrderActions()
        with pytest.raises(errors.InfraError):
            asyncio.run(actions.quote(order_actions.QuoteRequest(sku="widget")))
