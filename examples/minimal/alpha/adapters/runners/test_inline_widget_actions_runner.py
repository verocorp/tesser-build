from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.runners as runners
import alpha.adapters.runtimes as runtimes
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeAlphaApplicationClient(client.AlphaApplicationClient):

    def quote_widget(self, quote_widget_request: relays.QuoteWidgetRequest) -> relays.QuoteWidgetResponse:
        return relays.QuoteWidgetResponse(name=quote_widget_request.name)


class TestInlineWidgetActionsRunner:

    def test_running_a_quote_reaches_the_runtimes_handler(self) -> None:
        inline_widget_runtime = runtimes.InlineWidgetRuntime(FakeAlphaApplicationClient())
        quote_widget_response = runners.InlineWidgetActionsRunner(inline_widget_runtime).run_quote_widget(
            relays.QuoteWidgetRequest(name="a")
        )
        assert quote_widget_response.name == "a"
