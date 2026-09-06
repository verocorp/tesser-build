from __future__ import annotations

import tesser.adapters as ts

import parcel.application.ports as ports


class ParcelWireGateway(ts.Gateway):

    def to_payload(self, parcel_record: ports.ParcelRecord) -> ports.PayloadResponse:
        return ports.PayloadResponse(
            parcel_code=parcel_record.code,
            item_count=parcel_record.items,
            weight_kg=parcel_record.weight_kg,
            label_digest_hex=parcel_record.label_digest.hex(),
            declared_value=parcel_record.declared_value,
            scanned_at=parcel_record.scanned_at,
            weight_class=parcel_record.weight_class,
        )
