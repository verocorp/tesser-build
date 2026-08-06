from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])
C = TypeVar("C", bound=type)


def function(fn: F) -> F:
    return fn


def helper(fn: F) -> F:
    return fn


def fake(cls: C) -> C:
    return cls
