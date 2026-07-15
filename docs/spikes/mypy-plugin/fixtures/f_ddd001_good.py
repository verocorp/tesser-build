from dataclasses import dataclass


@dataclass(frozen=True)
class Temperature:
    celsius: float


t = Temperature(celsius=1.0)  # valid construction call, PASSING case
