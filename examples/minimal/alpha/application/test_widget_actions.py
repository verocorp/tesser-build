from __future__ import annotations

import tesser.testing as ts

import alpha.application as application
import alpha.application.ports as ports
import alpha.application.relays as relays


@ts.fake
class FakeWidgetRepository(ports.WidgetRepository):

    def __init__(self) -> None:
        self.saved: list[tuple[str, str]] = []

    def save(self, save_request: ports.SaveRequest) -> ports.SaveResponse:
        self.saved.append((save_request.name, save_request.standing))
        return ports.SaveResponse(name=save_request.name)


class TestWidgetActions:

    def test_quote_answers_the_named_widget(self) -> None:
        quote_response = application.WidgetActions(FakeWidgetRepository()).quote(
            relays.QuoteRequest(name="a")
        )
        assert quote_response.name == "a"

    def test_quote_calls_its_port_once(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        application.WidgetActions(fake_widget_repository).quote(relays.QuoteRequest(name="a"))
        assert [name for name, _ in fake_widget_repository.saved] == ["a"]

    def test_a_quoted_widget_is_saved_standing_kept(self) -> None:
        fake_widget_repository = FakeWidgetRepository()
        application.WidgetActions(fake_widget_repository).quote(relays.QuoteRequest(name="a"))
        assert fake_widget_repository.saved == [("a", "kept")]
