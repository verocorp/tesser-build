from __future__ import annotations

import enum
import typing


class _Auto(int):
    pass


class _Machinery(enum.Enum):
    pass


_GENERATED: typing.Final[frozenset[str]] = frozenset(_Machinery.__dict__)


def _gate(cls: type) -> None:
    members: dict[str, typing.Any] = cls.__dict__.get("_member_map_", {})
    if cls.__bases__ != (Outcome,):
        bases = ", ".join(base.__name__ for base in cls.__bases__)
        raise TypeError(
            f"{cls.__name__} subclasses {bases}: an outcome subclasses Outcome directly "
            "and alone, because a mixed-in base gives its members a value to compare "
            "against and a hierarchy reopens the closed set"
        )
    if cls.__dict__.get("_new_member_") is not object.__new__:
        raise TypeError(
            f"{cls.__name__} defines '__new__': an outcome is a closed set of names "
            "and nothing else — behavior belongs on the object that returns it"
        )
    generator = cls.__dict__.get("_generate_next_value_")
    if isinstance(generator, staticmethod):
        generator = generator.__func__
    if generator is not Outcome._generate_next_value_:
        raise TypeError(
            f"{cls.__name__} defines '_generate_next_value_': an outcome is a closed set "
            "of names and nothing else — behavior belongs on the object that returns it"
        )
    for name in cls.__dict__:
        if name in members or name in _GENERATED:
            continue
        raise TypeError(
            f"{cls.__name__} defines {name!r}: an outcome is a closed set of names "
            "and nothing else — behavior belongs on the object that returns it"
        )
    for member in members.values():
        if type(member._value_) is not _Auto:  # tesser:debt TB084
            raise TypeError(
                f"{cls.__name__}.{member._name_} carries a value: an outcome member "  # tesser:debt TB084
                "is enum.auto(), because an outcome is matched, never serialized"
            )
    names = cls.__dict__.get("_member_names_", [])
    for name, member in members.items():
        if name not in names:
            raise TypeError(
                f"{cls.__name__}.{name} repeats {cls.__name__}.{member._name_}: an outcome "  # tesser:debt TB084
                "member is a name of its own, because two names for one member make a "
                "case arm unreachable and exhaustiveness a lie"
            )


class _OutcomeMeta(enum.EnumMeta):

    def __new__(
        metacls,
        cls: str,
        bases: tuple[type, ...],
        classdict: enum._EnumDict,
        **kwargs: typing.Any,
    ) -> _OutcomeMeta:
        made = super().__new__(metacls, cls, bases, classdict, **kwargs)
        for base in bases:
            if isinstance(base, _OutcomeMeta):
                _gate(made)
                break
        return made


class Outcome(enum.Enum, metaclass=_OutcomeMeta):

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        return _Auto(count + 1)

    @property
    def value(self) -> object:
        raise TypeError(f"{type(self).__name__} is matched, never read: an outcome carries no value")

    @property
    def name(self) -> str:
        raise TypeError(f"{type(self).__name__} is matched, never read: an outcome carries no name")

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if type(cls) is not _OutcomeMeta:
            raise TypeError(
                f"{cls.__name__} uses a custom metaclass: an outcome is a closed set of names "
                "and nothing else — a metaclass is a home for behavior"
            )
