import typing

C = typing.TypeVar("C", bound=type)


def fake(cls: C) -> C:
    return cls
