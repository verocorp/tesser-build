from __future__ import annotations

import tesser.testing as ts

import alpha.application.ports.widget_actions as widget_actions
import alpha.application.ports.widget_repository as widget_repository
import alpha.application.widget_actions as actions


@ts.fake
class FakeWidgetRepository(widget_repository.WidgetRepository):

    def __init__(self) -> None:
        self.saved: list[str] = []

    def save(self, request: widget_repository.SaveRequest) -> widget_repository.SaveResponse:
        self.saved.append(request.name)
        return widget_repository.SaveResponse(name=request.name)


class TestWidgetActions:

    def test_quote_answers_the_named_widget(self) -> None:
        quoted = actions.WidgetActions(FakeWidgetRepository()).quote(
            widget_actions.QuoteRequest(name="a")
        )
        assert quoted.name == "a"

    def test_quote_calls_its_port_once(self) -> None:
        widgets = FakeWidgetRepository()
        actions.WidgetActions(widgets).quote(widget_actions.QuoteRequest(name="a"))
        assert widgets.saved == ["a"]
