import sys
import collections.abc as collections_abc
import typing


def main(run: collections_abc.Callable[[list[str]], int]) -> typing.NoReturn:  # tesser:debt TB022
    raise SystemExit(run(sys.argv[1:]))
