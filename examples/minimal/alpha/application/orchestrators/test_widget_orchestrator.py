from __future__ import annotations

import tesser.testing as ts

import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays


@ts.fake
class FakeWidgetActionsRelay(relays.WidgetActionsRelay):

    def __init__(self) -> None:
        self.kept: list[str] = []

    def run_keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        self.kept.append(keep_widget_request.name)
        return relays.KeepWidgetResponse(name=keep_widget_request.name)


class TestWidgetOrchestrator:

    def test_registering_answers_the_widget_the_action_kept(self) -> None:
        register_widget_response = orchestrators.WidgetOrchestrator(FakeWidgetActionsRelay()).register_widget(
            relays.RegisterWidgetRequest(name="a")
        )
        assert register_widget_response.name == "a"

    def test_registering_runs_its_relay_once(self) -> None:
        fake_widget_actions_relay = FakeWidgetActionsRelay()
        orchestrators.WidgetOrchestrator(fake_widget_actions_relay).register_widget(relays.RegisterWidgetRequest(name="a"))
        assert fake_widget_actions_relay.kept == ["a"]
