from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.runtimes as runtimes
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeAlphaApplicationClient(client.AlphaApplicationClient):

    def quote_widget(self, quote_widget_request: relays.QuoteWidgetRequest) -> relays.QuoteWidgetResponse:
        return relays.QuoteWidgetResponse(name=quote_widget_request.name)


class TestInlineWidgetRuntime:

    def test_the_quote_handler_reaches_the_application_client(self) -> None:
        inline_widget_runtime = runtimes.InlineWidgetRuntime(FakeAlphaApplicationClient())
        quote_widget_response = inline_widget_runtime.quote_handler(relays.QuoteWidgetRequest(name="a"))
        assert quote_widget_response.name == "a"

    def test_the_flow_handler_builds_the_orchestrator_it_runs(self) -> None:
        inline_widget_runtime = runtimes.InlineWidgetRuntime(FakeAlphaApplicationClient())
        flow_response = inline_widget_runtime.widget_flow_handler(relays.QuoteWidgetRequest(name="a"))
        assert flow_response.name == "a"
