from __future__ import annotations

import pytest

import tesser.testing as ts
import in_process

import alpha.adapters.activities as activities
import alpha.adapters.dispatchers as dispatchers
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


class TestInProcessWidgetOrchestratorRelay:

    def test_an_approved_widget_is_registered_through_the_engine_and_kept_once(self) -> None:
        fake_widget_application_client = FakeWidgetApplicationClient()
        widget_orchestrator_workflow = in_process.Workflow("WidgetOrchestrator")
        in_process_widget_orchestrator_relay = dispatchers.InProcessWidgetOrchestratorRelay(
            workflows.InProcessRegisterWidget(
                widget_orchestrator_workflow,
                activities.InProcessKeepWidget(in_process.Service("WidgetActions"), fake_widget_application_client),
            ),
            dispatchers.InProcessApproveWidget(widget_orchestrator_workflow),
        )
        approve_widget_response = in_process_widget_orchestrator_relay.run_approve_widget(
            relays.ApproveWidgetRequest(name="a")
        )
        register_widget_response = in_process_widget_orchestrator_relay.run_register_widget(
            relays.RegisterWidgetRequest(name="a")
        )
        assert approve_widget_response.name == "a"
        assert register_widget_response.name == "a"
        assert fake_widget_application_client.kept == ["a"]

    def test_an_approval_is_kept_for_the_widget_it_names_and_no_other(self) -> None:
        fake_widget_application_client = FakeWidgetApplicationClient()
        widget_orchestrator_workflow = in_process.Workflow("WidgetOrchestrator")
        in_process_widget_orchestrator_relay = dispatchers.InProcessWidgetOrchestratorRelay(
            workflows.InProcessRegisterWidget(
                widget_orchestrator_workflow,
                activities.InProcessKeepWidget(in_process.Service("WidgetActions"), fake_widget_application_client),
            ),
            dispatchers.InProcessApproveWidget(widget_orchestrator_workflow),
        )
        in_process_widget_orchestrator_relay.run_approve_widget(relays.ApproveWidgetRequest(name="a"))
        with pytest.raises(in_process.PromiseNotResolved):
            in_process_widget_orchestrator_relay.run_register_widget(relays.RegisterWidgetRequest(name="b"))
        assert fake_widget_application_client.kept == []


class TestInProcessApproveWidget:

    def test_the_engine_holds_approve_widget_beside_the_workflow_s_main(self) -> None:
        widget_orchestrator_workflow = in_process.Workflow("WidgetOrchestrator")
        in_process_approve_widget = dispatchers.InProcessApproveWidget(widget_orchestrator_workflow)
        assert widget_orchestrator_workflow.handlers == {"approve_widget": in_process_approve_widget.handler}
        assert widget_orchestrator_workflow.main_names == set()
