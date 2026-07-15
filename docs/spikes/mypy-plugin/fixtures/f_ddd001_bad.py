from dataclasses import dataclass


@dataclass
class Temperature:  # not frozen -- DDD001
    celsius: float


t = Temperature(celsius=1.0)  # valid construction call -- must still typecheck
