from dataclasses import dataclass


@dataclass(frozen=True)
class Labels:  # a value object (hidden field) — TB002 is a value-object rule
    _values: dict[str, str]  # mutable collection on a value object — TB002 (__hash__ raises)
