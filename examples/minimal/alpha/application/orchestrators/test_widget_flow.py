from __future__ import annotations

import tesser.testing as ts

import alpha.application.orchestrators.widget_flow as widget_flow
import alpha.application.ports.quoting as quoting


@ts.fake
class FakeQuoting(quoting.Quoting):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        self.quoted.append(request.name)
        return quoting.QuoteResponse(name=request.name)


class TestWidgetFlow:

    def test_the_flow_answers_what_the_action_quoted(self) -> None:
        ran = widget_flow.WidgetFlow(FakeQuoting()).run(
            quoting.QuoteRequest(name="a")
        )
        assert ran.name == "a"
