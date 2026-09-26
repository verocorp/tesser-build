import sys
import typing


class Command(typing.Protocol):

    def __call__(self, argv: list[str], /) -> int: ...


def main(run: Command) -> typing.NoReturn:
    raise SystemExit(run(sys.argv[1:]))
