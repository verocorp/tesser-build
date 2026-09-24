from __future__ import annotations

import tesser.adapters as ts
import in_process

import alpha.adapters.activities as activities
import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays


class InProcessInvocationWidgetActionsRelay(ts.Dispatcher):

    def __init__(
        self, in_process_workflow_context: in_process.WorkflowContext, in_process_keep_widget: activities.InProcessKeepWidget
    ) -> None:
        self._in_process_workflow_context = in_process_workflow_context
        self._in_process_keep_widget = in_process_keep_widget

    def run_keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        return self._in_process_workflow_context.service_call(self._in_process_keep_widget.handler, keep_widget_request)


class InProcessInvocationWidgetOrchestratorSignalRelay(ts.Dispatcher):

    def __init__(self, in_process_workflow_context: in_process.WorkflowContext) -> None:
        self._in_process_workflow_context = in_process_workflow_context

    def await_approve_widget(
        self, await_approve_widget_request: relays.AwaitApproveWidgetRequest
    ) -> relays.AwaitApproveWidgetResponse:
        return self._in_process_workflow_context.promise(
            relays.APPROVE_WIDGET_PROMISE, relays.AwaitApproveWidgetResponse
        ).value()


class InProcessRegisterWidget(ts.Workflow):

    def __init__(
        self, widget_orchestrator_workflow: in_process.Workflow, in_process_keep_widget: activities.InProcessKeepWidget
    ) -> None:
        @widget_orchestrator_workflow.main()
        def register_widget(
            in_process_workflow_context: in_process.WorkflowContext, register_widget_request: relays.RegisterWidgetRequest
        ) -> relays.RegisterWidgetResponse:
            return orchestrators.WidgetOrchestrator(
                InProcessInvocationWidgetOrchestratorSignalRelay(in_process_workflow_context),
                InProcessInvocationWidgetActionsRelay(in_process_workflow_context, in_process_keep_widget),
            ).register_widget(register_widget_request)

        self.handler = register_widget
