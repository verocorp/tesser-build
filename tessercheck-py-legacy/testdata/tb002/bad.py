from dataclasses import dataclass


@dataclass(frozen=True)
class Labels:
    _values: dict[str, str]
