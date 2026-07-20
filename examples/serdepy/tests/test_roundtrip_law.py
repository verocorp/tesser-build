from __future__ import annotations

from parcel import DeclaredValue, ItemCount, LabelDigest, ParcelCode, ScannedAt, WeightKg


def test_parcel_code_roundtrip() -> None:
    code = ParcelCode("PKG-2026-0042")
    assert ParcelCode(str(code)) == code


def test_item_count_roundtrip() -> None:
    count = ItemCount(3)
    assert ItemCount(int(count)) == count


def test_weight_roundtrip() -> None:
    weight = WeightKg(12.75)
    assert WeightKg(float(weight)) == weight


def test_label_digest_roundtrip() -> None:
    digest = LabelDigest(bytes(range(32)))
    assert LabelDigest(bytes(digest)) == digest


def test_declared_value_roundtrip() -> None:
    value = DeclaredValue("199.99")
    assert DeclaredValue(str(value)) == value


def test_scanned_at_roundtrip() -> None:
    scanned = ScannedAt("2026-07-20T15:16:15.123456+00:00")
    assert ScannedAt(str(scanned)) == scanned


def test_scanned_at_equal_instants_across_zones() -> None:
    utc = ScannedAt("2026-07-20T15:16:15.123456+00:00")
    eastern = ScannedAt("2026-07-20T10:16:15.123456-05:00")
    assert utc == eastern
    assert str(utc) == "2026-07-20T15:16:15.123456+00:00"
    assert str(eastern) == "2026-07-20T15:16:15.123456+00:00"
