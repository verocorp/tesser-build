"""Mars-Orbiter unit-swap: Meters and Seconds are distinct NewTypes; swapping
them at a call site is the bug class the Mars Climate Orbiter lost to a
primitive (unitless float) design -- should-flag."""
from dataclasses import dataclass
from typing import NewType

Meters = NewType("Meters", float)
Seconds = NewType("Seconds", float)


@dataclass(frozen=True)
class Trip:
    distance: Meters
    duration: Seconds


def combine(distance: Meters, duration: Seconds) -> float:
    return float(distance) / float(duration)


# BUG: units swapped at both a dataclass construction call and a plain call.
t = Trip(distance=Seconds(10.0), duration=Meters(5.0))
combine(distance=Seconds(10.0), duration=Meters(5.0))
