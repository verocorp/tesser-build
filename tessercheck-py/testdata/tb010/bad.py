from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) != 3:
            raise ValueError(self.value)


@dataclass(frozen=True)
class Slot:
    _key: str

    @property
    def key(self) -> str:
        return self._key

    def raw_key(self) -> str:
        return self._key
