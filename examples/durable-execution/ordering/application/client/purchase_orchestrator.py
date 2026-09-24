from __future__ import annotations

import typing

import tesser.application as ts

import ordering.application.relays as relays


class PurchaseOrchestratorApplicationClient(ts.Client, typing.Protocol):

    async def pay_for_order(
        self, pay_for_order_request: relays.PayForOrderRequest
    ) -> relays.PayForOrderResponse: ...
