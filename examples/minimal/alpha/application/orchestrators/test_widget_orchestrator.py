from __future__ import annotations

import tesser.testing as ts

import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays


@ts.fake
class FakeKeepWidgetRelay(relays.KeepWidgetRelay):

    def __init__(self) -> None:
        self.kept: list[str] = []

    def run_keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        self.kept.append(keep_widget_request.name)
        return relays.KeepWidgetResponse(name=keep_widget_request.name)


class TestWidgetOrchestrator:

    def test_registering_answers_the_widget_the_action_kept(self) -> None:
        register_widget_response = orchestrators.WidgetOrchestrator(FakeKeepWidgetRelay()).register_widget(
            relays.RegisterWidgetRequest(name="a")
        )
        assert register_widget_response.name == "a"

    def test_registering_runs_its_relay_once(self) -> None:
        fake_keep_widget_relay = FakeKeepWidgetRelay()
        orchestrators.WidgetOrchestrator(fake_keep_widget_relay).register_widget(relays.RegisterWidgetRequest(name="a"))
        assert fake_keep_widget_relay.kept == ["a"]
