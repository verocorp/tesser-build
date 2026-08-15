from __future__ import annotations

import math
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Final

import tesser.domain as ts

from tesser.serialization import (
    canonical_bytes,
    canonical_datetime,
    canonical_decimal,
    canonical_float,
    canonical_int,
    canonical_str,
)

_CODE_RE: Final[re.Pattern[str]] = re.compile(r"[A-Z0-9]([A-Z0-9-]{0,30}[A-Z0-9])?")
_DIGEST_LEN: Final[int] = 32
_HEAVY_KG: Final[float] = 20.0


class ParcelCode(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if not _CODE_RE.fullmatch(value):
            raise ValueError(f"parcel code {value!r} must be 1-32 uppercase alnum/hyphen")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class ItemCount(ts.ValueObject):

    def __init__(self, value: int) -> None:
        if value < 1:
            raise ValueError(f"item count must be positive: {value}")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return canonical_int(self._value)

    _value: int


class WeightClass(ts.ValueObject):

    def __init__(self, value: str) -> None:
        if value not in ("heavy", "standard"):
            raise ValueError(f"weight class must be heavy or standard: {value!r}")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)

    _value: str


class WeightKg(ts.ValueObject):

    def __init__(self, value: float) -> None:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"weight must be a positive finite number: {value}")
        object.__setattr__(self, "_value", value)

    def __float__(self) -> float:
        return canonical_float(self._value)

    def _exceeds(self, threshold: "WeightKg") -> bool:
        return self._value > threshold._value

    _value: float


class LabelDigest(ts.ValueObject):

    def __init__(self, value: bytes) -> None:
        if len(value) != _DIGEST_LEN:
            raise ValueError(f"label digest must be {_DIGEST_LEN} bytes, got {len(value)}")
        object.__setattr__(self, "_value", value)

    def __bytes__(self) -> bytes:
        return canonical_bytes(self._value)

    _value: bytes


class DeclaredValue(ts.ValueObject):

    def __init__(self, value: str) -> None:
        try:
            parsed = Decimal(value)
        except InvalidOperation as e:
            raise ValueError(f"invalid declared value: {value!r}") from e
        if parsed < 0:
            raise ValueError(f"declared value must not be negative: {parsed}")
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:
        return canonical_decimal(self._value)

    _value: Decimal


class ScannedAt(ts.ValueObject):

    def __init__(self, value: str) -> None:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as e:
            raise ValueError(f"invalid scan time: {value!r}") from e
        if parsed.tzinfo is None:
            raise ValueError(f"scan time must be timezone-aware: {value!r}")
        object.__setattr__(self, "_value", parsed)

    def __str__(self) -> str:
        return canonical_datetime(self._value)

    _value: datetime


class ParcelSpec(ts.Spec):

    def __init__(
        self,
        code: str,
        items: int,
        weight_kg: float,
        label_digest: bytes,
        declared_value: str,
        scanned_at: str,
    ) -> None:
        self.code = code
        self.items = items
        self.weight_kg = weight_kg
        self.label_digest = label_digest
        self.declared_value = declared_value
        self.scanned_at = scanned_at


class Parcel(ts.Entity):

    def __init__(self, spec: ParcelSpec) -> None:
        self._code = ParcelCode(spec.code)
        self._items = ItemCount(spec.items)
        self._weight = WeightKg(spec.weight_kg)
        self._label_digest = LabelDigest(spec.label_digest)
        self._declared_value = DeclaredValue(spec.declared_value)
        self._scanned_at = ScannedAt(spec.scanned_at)

    @property
    def code(self) -> ParcelCode:
        return self._code

    @property
    def items(self) -> ItemCount:
        return self._items

    @property
    def weight(self) -> WeightKg:
        return self._weight

    @property
    def label_digest(self) -> LabelDigest:
        return self._label_digest

    @property
    def declared_value(self) -> DeclaredValue:
        return self._declared_value

    @property
    def scanned_at(self) -> ScannedAt:
        return self._scanned_at

    def weight_class(self) -> WeightClass:
        heavy = self._weight._exceeds(WeightKg(_HEAVY_KG))
        return WeightClass("heavy" if heavy else "standard")

    @property
    def identity(self) -> ParcelCode:
        return self._code
