import collections.abc as collections_abc
import typing

F = typing.TypeVar("F", bound=collections_abc.Callable[..., object])  # tesser:debt TB022


def helper(fn: F) -> F:
    return fn
