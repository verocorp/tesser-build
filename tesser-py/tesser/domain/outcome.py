import enum


class Outcome(enum.Enum):

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        members = cls.__dict__.get("_member_map_", {})
        for name in cls.__dict__:
            if name.startswith("_") or name in members:
                continue
            raise TypeError(
                f"{cls.__name__} defines {name!r}: an outcome is a closed set of names "
                "and nothing else — behavior belongs on the object that returns it"
            )
        for member in members.values():
            if not isinstance(member.value, int):
                raise TypeError(
                    f"{cls.__name__}.{member.name} carries a value: an outcome member "
                    "is enum.auto(), because an outcome is matched, never serialized"
                )
