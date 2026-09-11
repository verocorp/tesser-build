from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.runtimes as runtimes
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeAlphaApplicationClient(client.AlphaApplicationClient):

    def quote(self, quote_request: relays.QuoteRequest) -> relays.QuoteResponse:
        return relays.QuoteResponse(name=quote_request.name)


class TestInlineWidgetRuntime:

    def test_the_quote_handler_reaches_the_application_client(self) -> None:
        inline_widget_runtime = runtimes.InlineWidgetRuntime(FakeAlphaApplicationClient())
        quote_response = inline_widget_runtime.quote_handler(relays.QuoteRequest(name="a"))
        assert quote_response.name == "a"

    def test_the_flow_handler_builds_the_orchestrator_it_runs(self) -> None:
        inline_widget_runtime = runtimes.InlineWidgetRuntime(FakeAlphaApplicationClient())
        flow_response = inline_widget_runtime.widget_flow_handler(relays.QuoteRequest(name="a"))
        assert flow_response.name == "a"
