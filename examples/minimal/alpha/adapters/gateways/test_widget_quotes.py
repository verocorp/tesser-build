from __future__ import annotations

import alpha.adapters.gateways.widget_quotes as widget_quotes
import alpha.application.ports.quoting as quoting


class TestWidgetQuoteGateway:

    def test_a_quote_answers_the_name_it_was_asked_for(self) -> None:
        quoted = widget_quotes.WidgetQuoteGateway().quote(
            quoting.QuoteRequest(name="a")
        )
        assert quoted.name == "a"
