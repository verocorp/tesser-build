from __future__ import annotations

import tesser.adapters as ts

import ordering.application.ports as ports


class MapToChargeResponse(ts.Mapper, ports.ChargeResponse):

    def __init__(self, charge_request: ports.ChargeRequest) -> None:
        super().__init__(
            order_id=charge_request.order_id,
            reference=f"pay-{charge_request.order_id}",
            cents=charge_request.cents,
        )


class MemoryPaymentProcessor(ts.Gateway):

    def __init__(self) -> None:
        self._receipts: dict[str, ports.ChargeResponse] = {}

    def charge(self, charge_request: ports.ChargeRequest) -> ports.ChargeResponse:
        return self._receipts.setdefault(charge_request.order_id, MapToChargeResponse(charge_request))

    def close(self) -> None:
        self._receipts.clear()
