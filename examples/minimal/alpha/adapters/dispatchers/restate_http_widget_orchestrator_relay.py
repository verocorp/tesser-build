from __future__ import annotations

import typing
import urllib.parse as urllib_parse

import tesser.adapters as ts
import httpx
import restate
import restate.client as restate_client
import restate.serde as restate_serde

import alpha.adapters.workflows as workflows
import alpha.application.relays as relays

_EMPTY_BODY: typing.Final[str] = "a message crosses the engine with a body"
_TIMEOUT: typing.Final[httpx.Timeout] = httpx.Timeout(5.0, read=30.0)
_FOREIGN_NAME: typing.Final[str] = "an approval names the widget its workflow is keyed by"
_ALREADY_COMPLETED: typing.Final[int] = 409
_ALREADY_COMPLETED_MESSAGE: typing.Final[str] = "promise was already completed"
_NOT_REGISTERING: typing.Final[int] = 412
_NOT_REGISTERING_MESSAGE: typing.Final[str] = "no registration of this widget has started, so there is nothing to approve"


class RestateApproveWidgetRequestSerde(ts.Serde, restate_serde.Serde[relays.ApproveWidgetRequest]):

    def serialize(self, approve_widget_request: relays.ApproveWidgetRequest | None) -> bytes:
        if approve_widget_request is None:
            return b""
        return relays.ApproveWidgetRequestSnapshot().serialize(approve_widget_request)

    def deserialize(self, buf: bytes) -> relays.ApproveWidgetRequest | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.ApproveWidgetRequestSnapshot().deserialize(buf)


class RestateApproveWidgetResponseSerde(ts.Serde, restate_serde.Serde[relays.ApproveWidgetResponse]):

    def serialize(self, approve_widget_response: relays.ApproveWidgetResponse | None) -> bytes:
        if approve_widget_response is None:
            return b""
        return relays.ApproveWidgetResponseSnapshot().serialize(approve_widget_response)

    def deserialize(self, buf: bytes) -> relays.ApproveWidgetResponse | None:
        if not buf:
            raise restate.TerminalError(_EMPTY_BODY, status_code=400)
        return relays.ApproveWidgetResponseSnapshot().deserialize(buf)


class RestateApproveWidget(ts.Signal):

    def __init__(self, widget_orchestrator_workflow: restate.Workflow) -> None:
        @widget_orchestrator_workflow.handler(
            input_serde=RestateApproveWidgetRequestSerde(),
            output_serde=RestateApproveWidgetResponseSerde(),
        )
        async def approve_widget(
            restate_workflow_shared_context: restate.WorkflowSharedContext,
            approve_widget_request: relays.ApproveWidgetRequest,
        ) -> relays.ApproveWidgetResponse:
            name = restate_workflow_shared_context.key()
            if approve_widget_request.name != name:
                raise restate.TerminalError(_FOREIGN_NAME, status_code=400)
            if (
                await restate_workflow_shared_context.get(relays.REGISTER_WIDGET_STATE, serde=restate_serde.BytesSerde())
                is None
            ):
                raise restate.TerminalError(_NOT_REGISTERING_MESSAGE, status_code=_NOT_REGISTERING)
            try:
                await restate_workflow_shared_context.promise(
                    relays.APPROVE_WIDGET_PROMISE, serde=restate_serde.BytesSerde()
                ).resolve(
                    relays.AwaitApproveWidgetResponseSnapshot().serialize(relays.AwaitApproveWidgetResponse(name=name))
                )
            except restate.TerminalError as terminal_error:
                if not (
                    terminal_error.status_code == _ALREADY_COMPLETED
                    and terminal_error.message == _ALREADY_COMPLETED_MESSAGE
                ):
                    raise
            return relays.ApproveWidgetResponse(name=name)

        self.handler = approve_widget


class RestateHttpWidgetOrchestratorRelay(ts.Dispatcher):

    def __init__(
        self,
        ingress: str,
        restate_register_widget: workflows.RestateRegisterWidget,
        restate_approve_widget: RestateApproveWidget,
    ) -> None:
        self._ingress = ingress
        self._restate_register_widget = restate_register_widget
        self._restate_approve_widget = restate_approve_widget

    async def start_register_widget(
        self, register_widget_request: relays.RegisterWidgetRequest
    ) -> relays.StartRegisterWidgetResponse:
        async with httpx.AsyncClient(base_url=self._ingress, timeout=_TIMEOUT) as async_client:
            await restate_client.Client(async_client).workflow_send(
                self._restate_register_widget.handler,
                key=urllib_parse.quote(str(register_widget_request.name), safe="").replace(".", "%2E"),
                arg=register_widget_request,
            )
        return relays.StartRegisterWidgetResponse(name=str(register_widget_request.name))

    async def run_approve_widget(self, approve_widget_request: relays.ApproveWidgetRequest) -> relays.ApproveWidgetResponse:
        async with httpx.AsyncClient(base_url=self._ingress, timeout=_TIMEOUT) as async_client:
            return await restate_client.Client(async_client).workflow_call(
                self._restate_approve_widget.handler,
                key=urllib_parse.quote(approve_widget_request.name, safe="").replace(".", "%2E"),
                arg=approve_widget_request,
            )
