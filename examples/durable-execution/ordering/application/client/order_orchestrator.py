from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays


class OrderOrchestratorApplicationClient(ts.Client, typing.Protocol):

    async def confirm_order(
        self, confirm_order_request: relays.ConfirmOrderRequest
    ) -> relays.ConfirmOrderResponse: ...


class OrderWorkflow[C](ts.Workflow, typing.Protocol):
    def invocation(
        self, context: C, /
    ) -> typing.AsyncContextManager[OrderOrchestratorApplicationClient]: ...
