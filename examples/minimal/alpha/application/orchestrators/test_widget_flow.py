from __future__ import annotations

import tesser.testing as ts

import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays


@ts.fake
class FakeWidgetActionsRunner(relays.WidgetActionsRunner):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    def run_quote(self, quote_request: relays.QuoteRequest) -> relays.QuoteResponse:
        self.quoted.append(quote_request.name)
        return relays.QuoteResponse(name=quote_request.name)


class TestWidgetFlow:

    def test_the_flow_answers_what_the_action_quoted(self) -> None:
        flow_response = orchestrators.WidgetFlow(FakeWidgetActionsRunner()).run(
            relays.QuoteRequest(name="a")
        )
        assert flow_response.name == "a"

    def test_the_flow_runs_its_relay_once(self) -> None:
        fake_widget_actions_runner = FakeWidgetActionsRunner()
        orchestrators.WidgetFlow(fake_widget_actions_runner).run(relays.QuoteRequest(name="a"))
        assert fake_widget_actions_runner.quoted == ["a"]
