from __future__ import annotations

import tesser.testing as ts

import alpha.application.orchestrators.widget_flow as widget_flow
import alpha.application.ports.widget_actions as widget_actions


@ts.fake
class FakeWidgetActions(widget_actions.WidgetActions):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    def quote(self, request: widget_actions.QuoteRequest) -> widget_actions.QuoteResponse:
        self.quoted.append(request.name)
        return widget_actions.QuoteResponse(name=request.name)


class TestWidgetFlow:

    def test_the_flow_answers_what_the_action_quoted(self) -> None:
        ran = widget_flow.WidgetFlow(FakeWidgetActions()).run(
            widget_actions.QuoteRequest(name="a")
        )
        assert ran.name == "a"
