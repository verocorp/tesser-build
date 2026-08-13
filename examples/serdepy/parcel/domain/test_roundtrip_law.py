from __future__ import annotations

import parcel.domain.parcel as parcel


def test_parcel_code_roundtrip() -> None:
    code = parcel.ParcelCode("PKG-2026-0042")
    assert parcel.ParcelCode(str(code)) == code


def test_item_count_roundtrip() -> None:
    count = parcel.ItemCount(3)
    assert parcel.ItemCount(int(count)) == count


def test_weight_roundtrip() -> None:
    weight = parcel.WeightKg(12.75)
    assert parcel.WeightKg(float(weight)) == weight


def test_label_digest_roundtrip() -> None:
    digest = parcel.LabelDigest(bytes(range(32)))
    assert parcel.LabelDigest(bytes(digest)) == digest


def test_declared_value_roundtrip() -> None:
    value = parcel.DeclaredValue("199.99")
    assert parcel.DeclaredValue(str(value)) == value


def test_scanned_at_roundtrip() -> None:
    scanned = parcel.ScannedAt("2026-07-20T15:16:15.123456+00:00")
    assert parcel.ScannedAt(str(scanned)) == scanned


def test_scanned_at_equal_instants_across_zones() -> None:
    utc = parcel.ScannedAt("2026-07-20T15:16:15.123456+00:00")
    eastern = parcel.ScannedAt("2026-07-20T10:16:15.123456-05:00")
    assert utc == eastern
    assert str(utc) == "2026-07-20T15:16:15.123456+00:00"
    assert str(eastern) == "2026-07-20T15:16:15.123456+00:00"
