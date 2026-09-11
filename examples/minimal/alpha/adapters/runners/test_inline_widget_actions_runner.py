from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.runners as runners
import alpha.adapters.runtimes as runtimes
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeAlphaApplicationClient(client.AlphaApplicationClient):

    def quote(self, quote_request: relays.QuoteRequest) -> relays.QuoteResponse:
        return relays.QuoteResponse(name=quote_request.name)


class TestInlineWidgetActionsRunner:

    def test_running_a_quote_reaches_the_runtimes_handler(self) -> None:
        inline_widget_runtime = runtimes.InlineWidgetRuntime(FakeAlphaApplicationClient())
        quote_response = runners.InlineWidgetActionsRunner(inline_widget_runtime).run_quote(
            relays.QuoteRequest(name="a")
        )
        assert quote_response.name == "a"
