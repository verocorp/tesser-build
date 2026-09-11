from __future__ import annotations

import json

import tesser.application as ts

import ordering.application.ports as ports
import ordering.domain as domain
import tesser.errors as errors


class OrderSnapshot(ts.Serde):

    def serialize(self, order: domain.Order) -> bytes:
        return json.dumps(
            {
                "order_id": str(order.identity),
                "sku": str(order.sku),
                "quantity": int(order.quantity),
            }
        ).encode()

    def deserialize(self, buf: bytes) -> domain.Order:  # tesser:debt TB081
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and isinstance(snapshot.get("sku"), str)
            and isinstance(snapshot.get("quantity"), int)
            and not isinstance(snapshot.get("quantity"), bool)
        ):
            raise ports.EngineRejected("an order snapshot is order_id, sku, and quantity")  # tesser:debt TB082
        try:  # tesser:debt TB082
            return domain.Order(
                domain.OrderSpec(
                    order_id=snapshot["order_id"],
                    sku=snapshot["sku"],
                    quantity=snapshot["quantity"],
                )
            )
        except errors.DomainError as domain_error:
            raise ports.EngineRejected(domain_error.message) from domain_error  # tesser:debt TB082
