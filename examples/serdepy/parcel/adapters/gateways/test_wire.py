from __future__ import annotations

import parcel.adapters.gateways.wire as wire
import parcel.application.ports.parcel_wire as parcel_wire


def test_to_payload_renames_every_record_field_onto_the_payload() -> None:
    record = parcel_wire.ParcelRecord(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value="199.99",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=parcel_wire.WeightClass.HEAVY,
    )
    response = wire.ParcelWireGateway().to_payload(record)
    assert response.parcel_code == "PKG-2026-0042"
    assert response.item_count == 3
    assert response.weight_kg == 21.5
    assert response.declared_value == "199.99"
    assert response.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert response.weight_class is parcel_wire.WeightClass.HEAVY


def test_to_payload_renders_the_label_digest_as_lowercase_hex() -> None:
    record = parcel_wire.ParcelRecord(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(range(32)),
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=parcel_wire.WeightClass.LIGHT,
    )
    response = wire.ParcelWireGateway().to_payload(record)
    assert response.label_digest_hex == (
        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )
    assert response.label_digest_hex == response.label_digest_hex.lower()
    assert len(response.label_digest_hex) == 64


def test_to_payload_distinguishes_digests_that_differ_in_one_byte() -> None:
    first = parcel_wire.ParcelRecord(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(32),
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=parcel_wire.WeightClass.LIGHT,
    )
    second = parcel_wire.ParcelRecord(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(31) + b"\x01",
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=parcel_wire.WeightClass.LIGHT,
    )
    gateway = wire.ParcelWireGateway()
    assert gateway.to_payload(first).label_digest_hex == "00" * 32
    assert gateway.to_payload(second).label_digest_hex == "00" * 31 + "01"


def test_to_payload_carries_the_light_weight_class_through() -> None:
    record = parcel_wire.ParcelRecord(
        code="SMALL-1",
        items=1,
        weight_kg=0.25,
        label_digest=bytes(32),
        declared_value="0.00",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=parcel_wire.WeightClass.LIGHT,
    )
    response = wire.ParcelWireGateway().to_payload(record)
    assert response.weight_class is parcel_wire.WeightClass.LIGHT


def test_to_payload_leaves_the_request_untouched() -> None:
    digest = bytes(range(32))
    record = parcel_wire.ParcelRecord(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=digest,
        declared_value="199.99",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=parcel_wire.WeightClass.HEAVY,
    )
    wire.ParcelWireGateway().to_payload(record)
    assert record.label_digest == digest
    assert record.code == "PKG-2026-0042"
    assert record.weight_class is parcel_wire.WeightClass.HEAVY


def test_the_gateway_answers_the_wire_port() -> None:
    port: parcel_wire.ParcelWire = wire.ParcelWireGateway()
    response = port.to_payload(
        parcel_wire.ParcelRecord(
            code="PKG-2026-0042",
            items=2,
            weight_kg=5.5,
            label_digest=bytes(32),
            declared_value="12.00",
            scanned_at="2026-07-20T15:16:15.123456+00:00",
            weight_class=parcel_wire.WeightClass.LIGHT,
        )
    )
    assert isinstance(response, parcel_wire.PayloadResponse)
    assert response.parcel_code == "PKG-2026-0042"
    assert response.item_count == 2
