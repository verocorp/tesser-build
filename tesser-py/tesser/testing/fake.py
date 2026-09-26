import typing

C = typing.TypeVar("C", bound=type)


def fake(cls: C) -> C:
    return cls


def peer(cls: C) -> C:
    return cls
