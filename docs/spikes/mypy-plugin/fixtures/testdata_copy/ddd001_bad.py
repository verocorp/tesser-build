from dataclasses import dataclass


@dataclass
class Temperature:  # not frozen — DDD001
    celsius: float
