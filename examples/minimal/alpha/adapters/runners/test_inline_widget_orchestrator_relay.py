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


class TestInlineWidgetOrchestratorRelay:

    def test_running_register_widget_reaches_the_runtimes_handler(self) -> None:
        inline_widget_runtime = runtimes.InlineWidgetRuntime(FakeAlphaApplicationClient())
        register_widget_response = runners.InlineWidgetOrchestratorRelay(inline_widget_runtime).run_register_widget(
            relays.RegisterWidgetRequest(name="a")
        )
        assert register_widget_response.name == "a"
