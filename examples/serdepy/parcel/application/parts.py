from __future__ import annotations

import tesser.application as ts

import parcel.domain.parcel as parcel


class ParcelParts(ts.Parts):

    def __init__(
        self,
        code: str,
        items: int,
        weight_kg: float,
        label_digest: bytes,
        declared_value: str,
        scanned_at: str,
        heavy: bool,
    ) -> None:
        self.code = code
        self.items = items
        self.weight_kg = weight_kg
        self.label_digest = label_digest
        self.declared_value = declared_value
        self.scanned_at = scanned_at
        self.heavy = heavy


@ts.function
def parcel_parts(p: parcel.Parcel) -> ParcelParts:
    return ParcelParts(
        code=str(p.code),
        items=int(p.items),
        weight_kg=float(p.weight),
        label_digest=bytes(p.label_digest),
        declared_value=str(p.declared_value),
        scanned_at=str(p.scanned_at),
        heavy=str(p.weight_class()) == "heavy",
    )
