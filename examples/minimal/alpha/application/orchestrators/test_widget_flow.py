from __future__ import annotations

import tesser.testing as ts

import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays


@ts.fake
class FakeWidgetActionsRunner(relays.WidgetActionsRunner):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    def run_quote_widget(self, quote_widget_request: relays.QuoteWidgetRequest) -> relays.QuoteWidgetResponse:
        self.quoted.append(quote_widget_request.name)
        return relays.QuoteWidgetResponse(name=quote_widget_request.name)


class TestWidgetFlow:

    def test_the_flow_answers_what_the_action_quoted(self) -> None:
        flow_response = orchestrators.WidgetFlow(FakeWidgetActionsRunner()).quote_widget(
            relays.QuoteWidgetRequest(name="a")
        )
        assert flow_response.name == "a"

    def test_the_flow_runs_its_relay_once(self) -> None:
        fake_widget_actions_runner = FakeWidgetActionsRunner()
        orchestrators.WidgetFlow(fake_widget_actions_runner).quote_widget(relays.QuoteWidgetRequest(name="a"))
        assert fake_widget_actions_runner.quoted == ["a"]
