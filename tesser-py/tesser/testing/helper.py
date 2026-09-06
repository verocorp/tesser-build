import collections.abc as abc
import typing

F = typing.TypeVar("F", bound=abc.Callable[..., object])  # tesser:debt TB022


def helper(fn: F) -> F:
    return fn
