from __future__ import annotations

import tesser.adapters as ts

import ordering.application.ports as ports
import tesser.errors as errors


class MemoryPaymentProcessor(ts.Gateway):

    def __init__(self) -> None:
        self._charges: dict[str, int] = {}

    def charge(self, charge_request: ports.ChargeRequest) -> ports.ChargeResponse:
        if charge_request.order_id in self._charges:
            raise errors.conflict(
                "payment_already_taken",
                f"order {charge_request.order_id!r} has already been charged",
            )
        self._charges[charge_request.order_id] = charge_request.cents
        return ports.ChargeResponse(
            reference=f"pay-{charge_request.order_id}", cents=charge_request.cents
        )

    def close(self) -> None:
        self._charges.clear()
