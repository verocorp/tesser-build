import collections.abc as abc
import typing

F = typing.TypeVar("F", bound=abc.Callable[..., object])  # tesser:debt TB022


def load(fn: F) -> F:
    return fn
