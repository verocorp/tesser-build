from __future__ import annotations

import parcel.adapters.wire as wire
import parcel.application.parts as parts
import parcel.domain.parcel as parcel


def test_wire_golden_locks_the_payload_shape() -> None:
    built = parcel.Parcel(
        parcel.ParcelSpec(
            code="PKG-2026-0042",
            items=3,
            weight_kg=21.5,
            label_digest=bytes(range(32)),
            declared_value="199.99",
            scanned_at="2026-07-20T10:16:15.123456-05:00",
        )
    )
    assert wire.to_payload(parts.parcel_parts(built)) == {
        "parcelCode": "PKG-2026-0042",
        "itemCount": 3,
        "weightKg": 21.5,
        "labelDigestHex": "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
        "declaredValue": "199.99",
        "scannedAt": "2026-07-20T15:16:15.123456+00:00",
        "heavy": True,
    }
