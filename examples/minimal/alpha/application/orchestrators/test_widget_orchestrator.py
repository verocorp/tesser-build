from __future__ import annotations

import tesser.testing as ts

import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays


@ts.fake
class FakeWidgetOrchestratorSignalRelay(relays.WidgetOrchestratorSignalRelay):

    def __init__(self, steps: list[str]) -> None:
        self._steps = steps

    def await_approve_widget(
        self, await_approve_widget_request: relays.AwaitApproveWidgetRequest
    ) -> relays.AwaitApproveWidgetResponse:
        self._steps.append("approved " + await_approve_widget_request.name)
        return relays.AwaitApproveWidgetResponse(name=await_approve_widget_request.name)


@ts.fake
class FakeWidgetActionsRelay(relays.WidgetActionsRelay):

    def __init__(self, steps: list[str]) -> None:
        self._steps = steps

    def run_keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        self._steps.append("kept " + keep_widget_request.name)
        return relays.KeepWidgetResponse(name=keep_widget_request.name)


class TestWidgetOrchestrator:

    def test_registering_answers_the_widget_the_action_kept(self) -> None:
        steps: list[str] = []
        register_widget_response = orchestrators.WidgetOrchestrator(
            FakeWidgetOrchestratorSignalRelay(steps), FakeWidgetActionsRelay(steps)
        ).register_widget(relays.RegisterWidgetRequest(name="a"))
        assert register_widget_response.name == "a"

    def test_registering_waits_for_the_approval_before_it_keeps_the_widget(self) -> None:
        steps: list[str] = []
        orchestrators.WidgetOrchestrator(
            FakeWidgetOrchestratorSignalRelay(steps), FakeWidgetActionsRelay(steps)
        ).register_widget(relays.RegisterWidgetRequest(name="a"))
        assert steps == ["approved a", "kept a"]
