from __future__ import annotations

import tesser.adapters as ts

import parcel.application.parts as parts


@ts.function
def to_payload(record: parts.ParcelParts) -> dict[str, object]:
    return {
        "parcelCode": record.code,
        "itemCount": record.items,
        "weightKg": record.weight_kg,
        "labelDigestHex": record.label_digest.hex(),
        "declaredValue": record.declared_value,
        "scannedAt": record.scanned_at,
        "heavy": record.heavy,
    }
