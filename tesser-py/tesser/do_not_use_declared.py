from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


def load(fn: F) -> F:
    return fn
