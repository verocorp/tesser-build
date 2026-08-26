import enum


class _Auto(int):
    pass


_GENERATED: frozenset[str] = frozenset()


class Outcome(enum.Enum):

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
        if not _GENERATED:
            return
        if type(cls) is not enum.EnumMeta:
            raise TypeError(
                f"{cls.__name__} uses a custom metaclass: an outcome is a closed set of names "
                "and nothing else — a metaclass is a home for behavior"
            )
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
        members = cls.__dict__.get("_member_map_", {})
        for name, attribute in cls.__dict__.items():
            if name in members or name in _GENERATED:
                continue
            if not (callable(attribute) or isinstance(attribute, (property, classmethod, staticmethod))):
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


class _Probe(Outcome):
    ONE = enum.auto()


_GENERATED = frozenset(_Probe.__dict__) - frozenset({"ONE"})
