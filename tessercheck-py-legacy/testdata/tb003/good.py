from dataclasses import dataclass


def canonical_str(value: str) -> str:
    return value


@dataclass(frozen=True)
class Slug:
    _value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "_value", self._value.lower())


@dataclass(frozen=True)
class GivenName:
    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("given name is required")

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class FamilyName:
    _value: str

    def __post_init__(self) -> None:
        if not self._value:
            raise ValueError("family name is required")

    def __str__(self) -> str:
        return canonical_str(self._value)


@dataclass(frozen=True)
class PersonNameSpec:
    given: str
    family: str


@dataclass(frozen=True, init=False)
class PersonName:
    _given: GivenName
    _family: FamilyName

    def __init__(self, spec: PersonNameSpec) -> None:
        object.__setattr__(self, "_given", GivenName(spec.given.strip()))
        object.__setattr__(self, "_family", FamilyName(spec.family.strip()))
