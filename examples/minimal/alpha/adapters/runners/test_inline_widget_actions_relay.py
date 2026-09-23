from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.runners as runners
import alpha.adapters.runtimes as runtimes
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeAlphaApplicationClient(client.AlphaApplicationClient):

    def keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        return relays.KeepWidgetResponse(name=keep_widget_request.name)


class TestInlineWidgetActionsRelay:

    def test_running_keep_widget_reaches_the_runtimes_handler(self) -> None:
        inline_widget_runtime = runtimes.InlineWidgetRuntime(FakeAlphaApplicationClient())
        keep_widget_response = runners.InlineWidgetActionsRelay(inline_widget_runtime).run_keep_widget(
            relays.KeepWidgetRequest(name="a")
        )
        assert keep_widget_response.name == "a"
