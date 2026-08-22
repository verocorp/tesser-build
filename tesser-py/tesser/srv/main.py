import sys
from collections.abc import Callable
from typing import NoReturn


def main(run: Callable[[list[str]], int]) -> NoReturn:
    raise SystemExit(run(sys.argv[1:]))
