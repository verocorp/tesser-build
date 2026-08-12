from dataclasses import dataclass


@dataclass(frozen=True)
class Temperature:
    celsius: float
