import collections.abc as abc
import typing

F = typing.TypeVar("F", bound=abc.Callable[..., object])


def helper(fn: F) -> F:
    return fn
