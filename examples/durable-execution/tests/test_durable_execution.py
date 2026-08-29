from __future__ import annotations

import asyncio

import app.loader as loader
import ordering.client.client as client


class TestWiredApp:

    def test_the_loaded_app_quotes_from_the_real_catalog(self) -> None:
        built = loader.load()
        try:
            quoted = built.ordering.actions.quote(client.QuoteRequest(sku="widget"))
        finally:
            asyncio.run(built.close())
        assert quoted.cents == 250

    def test_the_loaded_app_declares_the_restate_definitions_the_host_mounts(self) -> None:
        built = loader.load()
        try:
            declared = [d.name for d in built.ordering.handlers.definitions()]
        finally:
            asyncio.run(built.close())
        assert declared == ["Ordering", "OrderingActions"]
