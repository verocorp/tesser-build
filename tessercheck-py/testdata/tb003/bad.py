from dataclasses import dataclass


@dataclass(frozen=True)
class Slug:
    _value: str

    def normalize(self) -> None:
        object.__setattr__(self, "_value", self._value.lower())
