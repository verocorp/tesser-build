from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])


def do_not_use_function(fn: F) -> F:
    return fn


def load(fn: F) -> F:
    return fn
