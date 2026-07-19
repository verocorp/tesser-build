from dataclasses import dataclass


@dataclass(frozen=True)
class TargetURL:

    _value: str

    def __post_init__(self) -> None:
        if not (self._value.startswith("http://") or self._value.startswith("https://")):
            raise ValueError(
                f"invalid target URL {self._value!r}: must start with "
                "http:// or https://"
            )

    def __str__(self) -> str:
        return self._value
