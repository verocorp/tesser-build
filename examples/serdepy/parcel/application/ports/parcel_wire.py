from __future__ import annotations

import enum
from typing import Protocol

import tesser.application as ts


class WeightClass(enum.Enum):
    HEAVY = "heavy"
    LIGHT = "light"


class ParcelRecord(ts.Request):

    def __init__(
        self,
        code: str,
        items: int,
        weight_kg: float,
        label_digest: bytes,
        declared_value: str,
        scanned_at: str,
        weight_class: WeightClass,
    ) -> None:
        self.code = code
        self.items = items
        self.weight_kg = weight_kg
        self.label_digest = label_digest
        self.declared_value = declared_value
        self.scanned_at = scanned_at
        self.weight_class = weight_class


class PayloadResponse(ts.Response):

    def __init__(
        self,
        parcel_code: str,
        item_count: int,
        weight_kg: float,
        label_digest_hex: str,
        declared_value: str,
        scanned_at: str,
        weight_class: WeightClass,
    ) -> None:
        self.parcel_code = parcel_code
        self.item_count = item_count
        self.weight_kg = weight_kg
        self.label_digest_hex = label_digest_hex
        self.declared_value = declared_value
        self.scanned_at = scanned_at
        self.weight_class = weight_class


class ParcelWire(ts.Port, Protocol):

    def to_payload(self, request: ParcelRecord) -> PayloadResponse: ...
