import sys
import collections.abc as abc
import typing


def main(run: abc.Callable[[list[str]], int]) -> typing.NoReturn:
    raise SystemExit(run(sys.argv[1:]))
