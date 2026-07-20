from __future__ import annotations

from dataclasses import dataclass

from parcel import Parcel


@dataclass(frozen=True)
class ParcelParts:
    code: str
    items: int
    weight_kg: float
    label_digest: bytes
    declared_value: str
    scanned_at: str
    heavy: bool


def parcel_parts(p: Parcel) -> ParcelParts:
    return ParcelParts(
        code=str(p.code),
        items=int(p.items),
        weight_kg=float(p.weight),
        label_digest=bytes(p.label_digest),
        declared_value=str(p.declared_value),
        scanned_at=str(p.scanned_at),
        heavy=p.is_heavy(),
    )
