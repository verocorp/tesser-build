import sys

import pytest

import tesser.srv as srv


def test_main_hands_the_process_arguments_to_run_and_exits_with_its_code() -> None:
    class RecordingHost(srv.Host):

        def __init__(self) -> None:
            self.seen: list[list[str]] = []

        def run(self, argv: list[str]) -> int:
            self.seen.append(argv)
            return 3

    recording_host = RecordingHost()
    held = sys.argv
    sys.argv = ["prog", "--tree", "."]
    try:
        with pytest.raises(SystemExit) as leaving:
            srv.main(recording_host.run)
    finally:
        sys.argv = held
    assert recording_host.seen == [["--tree", "."]]
    assert leaving.value.code == 3


def test_main_exits_zero_when_run_returns_zero() -> None:
    class ZeroHost(srv.Host):

        def run(self, argv: list[str]) -> int:
            return 0

    held = sys.argv
    sys.argv = ["prog"]
    try:
        with pytest.raises(SystemExit) as leaving:
            srv.main(ZeroHost().run)
    finally:
        sys.argv = held
    assert leaving.value.code == 0
