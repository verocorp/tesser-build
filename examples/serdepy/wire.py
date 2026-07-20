from __future__ import annotations

from parts import ParcelParts


def to_payload(parts: ParcelParts) -> dict[str, object]:
    return {
        "parcelCode": parts.code,
        "itemCount": parts.items,
        "weightKg": parts.weight_kg,
        "labelDigestHex": parts.label_digest.hex(),
        "declaredValue": parts.declared_value,
        "scannedAt": parts.scanned_at,
        "heavy": parts.heavy,
    }
