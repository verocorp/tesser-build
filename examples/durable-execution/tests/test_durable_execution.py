from __future__ import annotations

import app.loader as loader
import ordering.client.client as client


class TestWiredApp:

    def test_the_loaded_app_quotes_from_the_real_catalog(self) -> None:
        app = loader.load()
        try:
            quoted = app.ordering.actions.quote(client.QuoteRequest(sku="widget"))
        finally:
            app.close()
        assert quoted.cents == 250

    def test_the_loaded_app_declares_the_restate_definitions_the_host_mounts(self) -> None:
        app = loader.load()
        try:
            declared = [d.name for d in app.ordering.handlers.definitions()]
        finally:
            app.close()
        assert declared == ["Ordering", "OrderingActions"]
