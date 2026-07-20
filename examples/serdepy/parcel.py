from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from serialization import (
    canonical_bytes,
    canonical_datetime,
    canonical_decimal,
    canonical_float,
    canonical_int,
    canonical_str,
)

_CODE_RE = re.compile(r"[A-Z0-9]([A-Z0-9-]{0,30}[A-Z0-9])?")
_DIGEST_LEN = 32
_HEAVY_KG = 20.0


@dataclass(frozen=True)
class ParcelCode:
    _value: str

    def __post_init__(self) -> None:
        if not _CODE_RE.fullmatch(self._value):
            raise ValueError(f"parcel code {self._value!r} must be 1-32 uppercase alnum/hyphen")

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class ItemCount:
    _value: int

    def __post_init__(self) -> None:
        if self._value < 1:
            raise ValueError(f"item count must be positive: {self._value}")

    def __int__(self) -> int:
        return canonical_int(self._value)


@dataclass(frozen=True)
class WeightKg:
    _value: float

    def __post_init__(self) -> None:
        if not math.isfinite(self._value) or self._value <= 0:
            raise ValueError(f"weight must be a positive finite number: {self._value}")

    def __float__(self) -> float:
        return canonical_float(self._value)

    def exceeds(self, threshold_kg: float) -> bool:
        return self._value > threshold_kg


@dataclass(frozen=True)
class LabelDigest:
    _value: bytes

    def __post_init__(self) -> None:
        if len(self._value) != _DIGEST_LEN:
            raise ValueError(f"label digest must be {_DIGEST_LEN} bytes, got {len(self._value)}")

    def __bytes__(self) -> bytes:
        return canonical_bytes(self._value)


@dataclass(frozen=True, init=False)
class DeclaredValue:
    _value: Decimal

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


@dataclass(frozen=True, init=False)
class ScannedAt:
    _value: datetime

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


@dataclass(frozen=True)
class ParcelSpec:
    code: str
    items: int
    weight_kg: float
    label_digest: bytes
    declared_value: str
    scanned_at: str


@dataclass(frozen=True, init=False)
class Parcel:
    _code: ParcelCode
    _items: ItemCount
    _weight: WeightKg
    _label_digest: LabelDigest
    _declared_value: DeclaredValue
    _scanned_at: ScannedAt

    def __init__(self, spec: ParcelSpec) -> None:
        object.__setattr__(self, "_code", ParcelCode(spec.code))
        object.__setattr__(self, "_items", ItemCount(spec.items))
        object.__setattr__(self, "_weight", WeightKg(spec.weight_kg))
        object.__setattr__(self, "_label_digest", LabelDigest(spec.label_digest))
        object.__setattr__(self, "_declared_value", DeclaredValue(spec.declared_value))
        object.__setattr__(self, "_scanned_at", ScannedAt(spec.scanned_at))

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

    def is_heavy(self) -> bool:
        return self._weight.exceeds(_HEAVY_KG)
