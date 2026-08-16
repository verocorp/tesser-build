from __future__ import annotations

import tesser.adapters as ts

import parcel.application.ports.parcel_wire as parcel_wire


class ParcelWireGateway(ts.Gateway):

    def to_payload(self, request: parcel_wire.ParcelRecord) -> parcel_wire.PayloadResponse:
        return parcel_wire.PayloadResponse(
            parcel_code=request.code,
            item_count=request.items,
            weight_kg=request.weight_kg,
            label_digest_hex=request.label_digest.hex(),
            declared_value=request.declared_value,
            scanned_at=request.scanned_at,
            weight_class=request.weight_class,
        )
