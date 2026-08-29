from __future__ import annotations

import asyncio
import typing

import restate

import ordering.application.ports.order_actions as order_actions
import ordering.component.component as component
import ordering.component.config as config


class TestOrdering:

    def test_the_wired_quote_job_quotes_from_the_catalog(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        try:
            quoted = asyncio.run(
                wired.jobs.quote(
                    typing.cast(restate.Context, None), order_actions.QuoteRequest(sku="widget")
                )
            )
        finally:
            wired.close()
        assert quoted.cents == 250

    def test_the_component_publishes_the_restate_definitions_it_wired(self) -> None:
        wired = component.Ordering(config.Config(config.Spec(ingress="http://localhost:8080")))
        try:
            declared = [d.name for d in wired.jobs.definitions()]
        finally:
            wired.close()
        assert declared == ["Ordering", "OrderingActions"]
