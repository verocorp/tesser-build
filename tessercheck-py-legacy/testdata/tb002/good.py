from dataclasses import dataclass


@dataclass(frozen=True)
class Labels:
    _values: tuple[tuple[str, str], ...] = ()
