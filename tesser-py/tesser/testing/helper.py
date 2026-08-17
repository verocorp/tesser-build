from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


def helper(fn: F) -> F:
    return fn
