from __future__ import annotations

import parcel.adapters.gateways as gateways
import parcel.application.ports as ports


def test_manifest_parcel_renames_every_record_field_onto_the_payload() -> None:
    manifest_parcel_request = ports.ManifestParcelRequest(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=bytes(range(32)),
        declared_value="199.99",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.HEAVY,
    )
    manifest_parcel_response = gateways.ParcelWireGateway().manifest_parcel(manifest_parcel_request)
    assert manifest_parcel_response.parcel.parcel_code == "PKG-2026-0042"
    assert manifest_parcel_response.parcel.item_count == 3
    assert manifest_parcel_response.parcel.weight_kg == 21.5
    assert manifest_parcel_response.parcel.declared_value == "199.99"
    assert manifest_parcel_response.parcel.scanned_at == "2026-07-20T15:16:15.123456+00:00"
    assert manifest_parcel_response.parcel.weight_class is ports.WeightClass.HEAVY


def test_manifest_parcel_renders_the_label_digest_as_lowercase_hex() -> None:
    manifest_parcel_request = ports.ManifestParcelRequest(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(range(32)),
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.LIGHT,
    )
    manifest_parcel_response = gateways.ParcelWireGateway().manifest_parcel(manifest_parcel_request)
    assert manifest_parcel_response.parcel.label_digest_hex == (
        "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
    )
    assert manifest_parcel_response.parcel.label_digest_hex == manifest_parcel_response.parcel.label_digest_hex.lower()
    assert len(manifest_parcel_response.parcel.label_digest_hex) == 64


def test_manifest_parcel_distinguishes_digests_that_differ_in_one_byte() -> None:
    first = ports.ManifestParcelRequest(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(32),
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.LIGHT,
    )
    second = ports.ManifestParcelRequest(
        code="PKG-2026-0042",
        items=1,
        weight_kg=1.0,
        label_digest=bytes(31) + b"\x01",
        declared_value="0",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.LIGHT,
    )
    parcel_wire_gateway = gateways.ParcelWireGateway()
    assert parcel_wire_gateway.manifest_parcel(first).parcel.label_digest_hex == "00" * 32
    assert parcel_wire_gateway.manifest_parcel(second).parcel.label_digest_hex == "00" * 31 + "01"


def test_manifest_parcel_carries_the_light_weight_class_through() -> None:
    manifest_parcel_request = ports.ManifestParcelRequest(
        code="SMALL-1",
        items=1,
        weight_kg=0.25,
        label_digest=bytes(32),
        declared_value="0.00",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.LIGHT,
    )
    manifest_parcel_response = gateways.ParcelWireGateway().manifest_parcel(manifest_parcel_request)
    assert manifest_parcel_response.parcel.weight_class is ports.WeightClass.LIGHT


def test_manifest_parcel_leaves_the_request_untouched() -> None:
    digest = bytes(range(32))
    manifest_parcel_request = ports.ManifestParcelRequest(
        code="PKG-2026-0042",
        items=3,
        weight_kg=21.5,
        label_digest=digest,
        declared_value="199.99",
        scanned_at="2026-07-20T15:16:15.123456+00:00",
        weight_class=ports.WeightClass.HEAVY,
    )
    gateways.ParcelWireGateway().manifest_parcel(manifest_parcel_request)
    assert manifest_parcel_request.label_digest == digest
    assert manifest_parcel_request.code == "PKG-2026-0042"
    assert manifest_parcel_request.weight_class is ports.WeightClass.HEAVY


def test_the_gateway_answers_the_wire_port() -> None:
    parcel_wire_gateway: ports.ParcelWire = gateways.ParcelWireGateway()
    manifest_parcel_response = parcel_wire_gateway.manifest_parcel(
        ports.ManifestParcelRequest(
            code="PKG-2026-0042",
            items=2,
            weight_kg=5.5,
            label_digest=bytes(32),
            declared_value="12.00",
            scanned_at="2026-07-20T15:16:15.123456+00:00",
            weight_class=ports.WeightClass.LIGHT,
        )
    )
    assert isinstance(manifest_parcel_response, ports.ManifestParcelResponse)
    assert manifest_parcel_response.parcel.parcel_code == "PKG-2026-0042"
    assert manifest_parcel_response.parcel.item_count == 2
