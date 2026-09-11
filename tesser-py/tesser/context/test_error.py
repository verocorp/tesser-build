import pytest

import tesser.context.error as error


class _Rejected(error.Error):

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def test_error_is_an_exception() -> None:
    assert issubclass(error.Error, Exception)


def test_a_context_declares_its_own_errors_beneath_the_root() -> None:
    with pytest.raises(error.Error) as raised:
        raise _Rejected("empty_name")
    assert isinstance(raised.value, _Rejected)
    assert raised.value.code == "empty_name"


def test_the_root_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(error.Error) if not name.startswith("_")}
    assert own == set(), own
