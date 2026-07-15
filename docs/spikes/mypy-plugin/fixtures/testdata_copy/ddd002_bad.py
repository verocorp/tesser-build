from dataclasses import dataclass


@dataclass(frozen=True)
class Labels:
    values: dict[str, str]  # mutable collection field — DDD002 (__hash__ raises)
