from __future__ import annotations

import tesser.application as ts

import parcel.application.ports.parcel_wire as parcel_wire
import parcel.domain.parcel as parcel


@ts.function
def parcel_record(p: parcel.Parcel) -> parcel_wire.ParcelRecord:
    return parcel_wire.ParcelRecord(
        code=str(p.code),
        items=int(p.items),
        weight_kg=float(p.weight),
        label_digest=bytes(p.label_digest),
        declared_value=str(p.declared_value),
        scanned_at=str(p.scanned_at),
        weight_class=(
            parcel_wire.WeightClass.HEAVY
            if str(p.weight_class()) == "heavy"
            else parcel_wire.WeightClass.LIGHT
        ),
    )
