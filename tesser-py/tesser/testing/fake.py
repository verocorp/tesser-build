from typing import TypeVar

C = TypeVar("C", bound=type)


def fake(cls: C) -> C:
    return cls
