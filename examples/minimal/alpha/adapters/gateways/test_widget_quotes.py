from __future__ import annotations

import alpha.adapters.gateways.widget_quotes as widget_quotes
import alpha.application.ports.widget_actions as widget_actions


class TestWidgetQuoteGateway:

    def test_a_quote_answers_the_name_it_was_asked_for(self) -> None:
        quoted = widget_quotes.WidgetQuoteGateway().quote(
            widget_actions.QuoteRequest(name="a")
        )
        assert quoted.name == "a"
