import collections.abc as collections_abc
import typing

F = typing.TypeVar("F", bound=collections_abc.Callable[..., object])  # tesser:debt TB022


def load(fn: F) -> F:
    return fn
