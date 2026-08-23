import sys

import pytest

from tesser.srv.main import main


def test_main_hands_the_process_arguments_to_run_and_exits_with_its_code() -> None:
    seen: list[list[str]] = []

    def run(argv: list[str]) -> int:
        seen.append(argv)
        return 3

    held = sys.argv
    sys.argv = ["prog", "--tree", "."]
    try:
        with pytest.raises(SystemExit) as leaving:
            main(run)
    finally:
        sys.argv = held
    assert seen == [["--tree", "."]]
    assert leaving.value.code == 3


def test_main_exits_zero_when_run_returns_zero() -> None:
    held = sys.argv
    sys.argv = ["prog"]
    try:
        with pytest.raises(SystemExit) as leaving:
            main(lambda argv: 0)
    finally:
        sys.argv = held
    assert leaving.value.code == 0
