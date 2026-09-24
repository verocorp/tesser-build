from __future__ import annotations

import tesser.adapters as ts
import in_process

import alpha.adapters.workflows as workflows
import alpha.application.relays as relays


class InProcessApproveWidget(ts.Signal):

    def __init__(self, widget_orchestrator_workflow: in_process.Workflow) -> None:
        @widget_orchestrator_workflow.handler()
        def approve_widget(
            in_process_workflow_shared_context: in_process.WorkflowSharedContext,
            approve_widget_request: relays.ApproveWidgetRequest,
        ) -> relays.ApproveWidgetResponse:
            name = in_process_workflow_shared_context.key()
            in_process_workflow_shared_context.promise(
                relays.APPROVE_WIDGET_PROMISE, relays.AwaitApproveWidgetResponse
            ).resolve(relays.AwaitApproveWidgetResponse(name=name))
            return relays.ApproveWidgetResponse(name=name)

        self.handler = approve_widget


class InProcessWidgetOrchestratorRelay(ts.Dispatcher):

    def __init__(
        self,
        in_process_register_widget: workflows.InProcessRegisterWidget,
        in_process_approve_widget: InProcessApproveWidget,
    ) -> None:
        self._in_process_register_widget = in_process_register_widget
        self._in_process_approve_widget = in_process_approve_widget

    def run_register_widget(self, register_widget_request: relays.RegisterWidgetRequest) -> relays.RegisterWidgetResponse:
        return in_process.workflow_call(
            self._in_process_register_widget.handler, key=register_widget_request.name, arg=register_widget_request
        )

    def run_approve_widget(self, approve_widget_request: relays.ApproveWidgetRequest) -> relays.ApproveWidgetResponse:
        return in_process.workflow_call(
            self._in_process_approve_widget.handler, key=approve_widget_request.name, arg=approve_widget_request
        )
