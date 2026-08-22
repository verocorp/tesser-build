from __future__ import annotations

import parcel.adapters.gateways.wire as wire
import parcel.application.ports.parcel_wire as parcel_wire
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
    record = parcel_wire.ParcelRecord(
        code=str(built.code),
        items=int(built.items),
        weight_kg=float(built.weight),
        label_digest=bytes(built.label_digest),
        declared_value=str(built.declared_value),
        scanned_at=str(built.scanned_at),
        weight_class=(
            parcel_wire.WeightClass.HEAVY
            if str(built.weight_class()) == "heavy"
            else parcel_wire.WeightClass.LIGHT
        ),
    )
    response = wire.ParcelWireGateway().to_payload(record)
    assert response.parcel_code == "PKG-2026-0042"
    assert response.item_count == 3
    assert response.weight_kg == 21.5
    assert response.label_digest_hex == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    assert response.declared_value == "199.99"
    assert response.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert response.weight_class is parcel_wire.WeightClass.HEAVY
