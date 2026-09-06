from __future__ import annotations

import parcel.adapters.gateways as gateways
import parcel.application.ports as ports


def test_to_payload_renames_every_record_field_onto_the_payload() -> None:
    parcel_record = ports.ParcelRecord(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value="199.99",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.HEAVY,
    )
    payload_response = gateways.ParcelWireGateway().to_payload(parcel_record)
    assert payload_response.parcel_code == "PKG-2026-0042"
    assert payload_response.item_count == 3
    assert payload_response.weight_kg == 21.5
    assert payload_response.declared_value == "199.99"
    assert payload_response.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert payload_response.weight_class is ports.WeightClass.HEAVY


def test_to_payload_renders_the_label_digest_as_lowercase_hex() -> None:
    parcel_record = ports.ParcelRecord(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(range(32)),
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.LIGHT,
    )
    payload_response = gateways.ParcelWireGateway().to_payload(parcel_record)
    assert payload_response.label_digest_hex == (
        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )
    assert payload_response.label_digest_hex == payload_response.label_digest_hex.lower()
    assert len(payload_response.label_digest_hex) == 64


def test_to_payload_distinguishes_digests_that_differ_in_one_byte() -> None:
    first = ports.ParcelRecord(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(32),
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.LIGHT,
    )
    second = ports.ParcelRecord(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(31) + b"\x01",
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.LIGHT,
    )
    parcel_wire_gateway = gateways.ParcelWireGateway()
    assert parcel_wire_gateway.to_payload(first).label_digest_hex == "00" * 32
    assert parcel_wire_gateway.to_payload(second).label_digest_hex == "00" * 31 + "01"


def test_to_payload_carries_the_light_weight_class_through() -> None:
    parcel_record = ports.ParcelRecord(
        code="SMALL-1",
        items=1,
        weight_kg=0.25,
        label_digest=bytes(32),
        declared_value="0.00",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.LIGHT,
    )
    payload_response = gateways.ParcelWireGateway().to_payload(parcel_record)
    assert payload_response.weight_class is ports.WeightClass.LIGHT


def test_to_payload_leaves_the_request_untouched() -> None:
    digest = bytes(range(32))
    parcel_record = ports.ParcelRecord(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=digest,
        declared_value="199.99",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.HEAVY,
    )
    gateways.ParcelWireGateway().to_payload(parcel_record)
    assert parcel_record.label_digest == digest
    assert parcel_record.code == "PKG-2026-0042"
    assert parcel_record.weight_class is ports.WeightClass.HEAVY


def test_the_gateway_answers_the_wire_port() -> None:
    parcel_wire_gateway: ports.ParcelWire = gateways.ParcelWireGateway()
    payload_response = parcel_wire_gateway.to_payload(
        ports.ParcelRecord(
            code="PKG-2026-0042",
            items=2,
            weight_kg=5.5,
            label_digest=bytes(32),
            declared_value="12.00",
            scanned_at="2026-07-20T15:16:15.123456+00:00",
            weight_class=ports.WeightClass.LIGHT,
        )
    )
    assert isinstance(payload_response, ports.PayloadResponse)
    assert payload_response.parcel_code == "PKG-2026-0042"
    assert payload_response.item_count == 2
