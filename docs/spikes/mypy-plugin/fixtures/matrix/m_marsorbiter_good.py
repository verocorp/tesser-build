"""Same NewType unit setup, correct units at every call site -- should-pass."""
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


t = Trip(distance=Meters(10.0), duration=Seconds(5.0))
combine(distance=Meters(10.0), duration=Seconds(5.0))
