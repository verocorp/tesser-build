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
    manifest_parcel_request = ports.ManifestParcelRequest(
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
    manifest_parcel_response = gateways.ParcelWireGateway().manifest_parcel(manifest_parcel_request)
    assert manifest_parcel_response.parcel.parcel_code == "PKG-2026-0042"
    assert manifest_parcel_response.parcel.item_count == 3
    assert manifest_parcel_response.parcel.weight_kg == 21.5
    assert manifest_parcel_response.parcel.label_digest_hex == "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    assert manifest_parcel_response.parcel.declared_value == "199.99"
    assert manifest_parcel_response.parcel.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert manifest_parcel_response.parcel.weight_class is ports.WeightClass.HEAVY
