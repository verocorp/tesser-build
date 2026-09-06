from __future__ import annotations

import tesser.testing as ts

import alpha.application.ports as ports
import alpha.application.widget_actions as widget_actions
import alpha.domain as domain


@ts.fake
class FakeWidgetRepository(ports.WidgetRepository):

    def __init__(self) -> None:
        self.saved: list[str] = []

    def save(self, save_request: ports.SaveRequest) -> ports.SaveResponse:
        self.saved.append(save_request.name)
        return ports.SaveResponse(name=save_request.name)


class TestWidgetActions:

    def test_quote_answers_the_named_widget(self) -> None:
        quoted = widget_actions.WidgetActions(FakeWidgetRepository()).quote(
            ports.QuoteRequest(name="a")
        )
        assert quoted.name == "a"

    def test_quote_calls_its_port_once(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        widget_actions.WidgetActions(fake_widget_repository).quote(ports.QuoteRequest(name="a"))
        assert fake_widget_repository.saved == ["a"]

    def test_a_quoted_widget_is_saved_standing_kept(self) -> None:
        assert widget_actions.MapToSaveRequest(domain.Name("a")).standing == "kept"
