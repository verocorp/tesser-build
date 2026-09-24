from __future__ import annotations

import pytest

import tesser.testing as ts
import in_process

import alpha.adapters.activities as activities
import alpha.adapters.workflows as workflows
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeWidgetApplicationClient(client.WidgetApplicationClient):

    def __init__(self) -> None:
        self.kept: list[str] = []

    def keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        self.kept.append(keep_widget_request.name)
        return relays.KeepWidgetResponse(name=keep_widget_request.name)


class TestInProcessRegisterWidget:

    def test_the_engine_holds_register_widget_as_the_workflow_s_main(self) -> None:
        widget_orchestrator_workflow = in_process.Workflow("WidgetOrchestrator")
        in_process_register_widget = workflows.InProcessRegisterWidget(
            widget_orchestrator_workflow,
            activities.InProcessKeepWidget(in_process.Service("WidgetActions"), FakeWidgetApplicationClient()),
        )
        assert widget_orchestrator_workflow.handlers == {"register_widget": in_process_register_widget.handler}
        assert widget_orchestrator_workflow.main_names == {"register_widget"}

    def test_a_registration_nobody_approved_stops_at_the_approval_and_keeps_nothing(self) -> None:
        fake_widget_application_client = FakeWidgetApplicationClient()
        in_process_register_widget = workflows.InProcessRegisterWidget(
            in_process.Workflow("WidgetOrchestrator"),
            activities.InProcessKeepWidget(in_process.Service("WidgetActions"), fake_widget_application_client),
        )
        with pytest.raises(in_process.PromiseNotResolved) as raised:
            in_process.workflow_call(
                in_process_register_widget.handler, key="a", arg=relays.RegisterWidgetRequest(name="a")
            )
        assert str(raised.value) == relays.APPROVE_WIDGET_PROMISE
        assert fake_widget_application_client.kept == []
