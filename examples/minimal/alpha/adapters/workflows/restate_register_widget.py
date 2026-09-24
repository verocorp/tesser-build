from __future__ import annotations

import typing

import tesser.adapters as ts
import restate
import restate.serde as restate_serde

import alpha.adapters.activities as activities
import alpha.application.orchestrators as orchestrators
import alpha.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"
_FOREIGN_NAME: typing.Final[str] = "a registration names the widget its workflow is keyed by"


class RestateRegisterWidgetRequestSerde(ts.Serde, restate_serde.Serde[relays.RegisterWidgetRequest]):

    def serialize(self, register_widget_request: relays.RegisterWidgetRequest | None) -> bytes:
        if register_widget_request is None:
            return b""
        return relays.RegisterWidgetRequestSnapshot().serialize(register_widget_request)

    def deserialize(self, buf: bytes) -> relays.RegisterWidgetRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.RegisterWidgetRequestSnapshot().deserialize(buf)


class RestateRegisterWidgetResponseSerde(ts.Serde, restate_serde.Serde[relays.RegisterWidgetResponse]):

    def serialize(self, register_widget_response: relays.RegisterWidgetResponse | None) -> bytes:
        if register_widget_response is None:
            return b""
        return relays.RegisterWidgetResponseSnapshot().serialize(register_widget_response)

    def deserialize(self, buf: bytes) -> relays.RegisterWidgetResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.RegisterWidgetResponseSnapshot().deserialize(buf)


class RestateInvocationWidgetActionsRelay(ts.Dispatcher):

    def __init__(
        self, restate_workflow_context: restate.WorkflowContext, restate_keep_widget: activities.RestateKeepWidget
    ) -> None:
        self._restate_workflow_context = restate_workflow_context
        self._restate_keep_widget = restate_keep_widget

    async def run_keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        return await self._restate_workflow_context.service_call(self._restate_keep_widget.handler, keep_widget_request)


class RestateInvocationWidgetOrchestratorSignalRelay(ts.Dispatcher):

    def __init__(self, restate_workflow_context: restate.WorkflowContext) -> None:
        self._restate_workflow_context = restate_workflow_context

    async def await_approve_widget(
        self, await_approve_widget_request: relays.AwaitApproveWidgetRequest
    ) -> relays.AwaitApproveWidgetResponse:
        return relays.AwaitApproveWidgetResponseSnapshot().deserialize(
            await self._restate_workflow_context.promise(
                relays.APPROVE_WIDGET_PROMISE, serde=restate_serde.BytesSerde()
            ).value()
        )


class RestateRegisterWidget(ts.Workflow):

    def __init__(
        self, widget_orchestrator_workflow: restate.Workflow, restate_keep_widget: activities.RestateKeepWidget
    ) -> None:
        @widget_orchestrator_workflow.main(
            input_serde=RestateRegisterWidgetRequestSerde(),
            output_serde=RestateRegisterWidgetResponseSerde(),
        )
        async def register_widget(
            restate_workflow_context: restate.WorkflowContext, register_widget_request: relays.RegisterWidgetRequest
        ) -> relays.RegisterWidgetResponse:
            if str(register_widget_request.name) != restate_workflow_context.key():
                raise restate.TerminalError(_FOREIGN_NAME, status_code=400)
            return await orchestrators.WidgetOrchestrator(
                RestateInvocationWidgetOrchestratorSignalRelay(restate_workflow_context),
                RestateInvocationWidgetActionsRelay(restate_workflow_context, restate_keep_widget),
            ).register_widget(register_widget_request)

        self.handler = register_widget
