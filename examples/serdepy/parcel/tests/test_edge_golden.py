from __future__ import annotations

import parcel.adapters.gateways as gateways
import parcel.application.ports as ports
import parcel.domain as domain


def test_wire_golden_locks_the_payload_shape() -> None:
    parcel = domain.Parcel(
        domain.ParcelSpec(
            code="PKG-2026-0042",
            items=3,
            weight_kg=21.5,
            label_digest=bytes(range(32)),
            declared_value="199.99",
            scanned_at="2026-07-20T10:16:15.123456-05:00",
        )
    )
    parcel_record = ports.ParcelRecord(
        code=str(parcel.code),
        items=int(parcel.items),
        weight_kg=float(parcel.weight),
        label_digest=bytes(parcel.label_digest),
        declared_value=str(parcel.declared_value),
        scanned_at=str(parcel.scanned_at),
        weight_class=(
            ports.WeightClass.HEAVY
            if str(parcel.weight_class()) == "heavy"
            else ports.WeightClass.LIGHT
        ),
    )
    payload_response = gateways.ParcelWireGateway().to_payload(parcel_record)
    assert payload_response.parcel_code == "PKG-2026-0042"
    assert payload_response.item_count == 3
    assert payload_response.weight_kg == 21.5
    assert payload_response.label_digest_hex == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    assert payload_response.declared_value == "199.99"
    assert payload_response.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert payload_response.weight_class is ports.WeightClass.HEAVY
