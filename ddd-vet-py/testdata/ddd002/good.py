from dataclasses import dataclass


@dataclass(frozen=True)
class Labels:  # a value object (hidden field) — DDD002 is a value-object rule
    _values: tuple[tuple[str, str], ...] = ()  # hashable storage on a value object
