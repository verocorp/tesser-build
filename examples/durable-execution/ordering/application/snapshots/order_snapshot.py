from __future__ import annotations

import json

import tesser.application as ts

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

    def deserialize(self, buf: bytes) -> domain.Order:
        snapshot = json.loads(buf)
        if not (
            isinstance(snapshot, dict)
            and isinstance(snapshot.get("order_id"), str)
            and isinstance(snapshot.get("sku"), str)
            and isinstance(snapshot.get("quantity"), int)
            and not isinstance(snapshot.get("quantity"), bool)
        ):
            raise errors.invalid("malformed_order_snapshot", "an order snapshot is order_id, sku, and quantity")
        return domain.Order(
            domain.OrderSpec(
                order_id=snapshot["order_id"],
                sku=snapshot["sku"],
                quantity=snapshot["quantity"],
            )
        )
