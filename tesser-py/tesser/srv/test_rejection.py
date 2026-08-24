import pytest

import tesser.srv.rejection as rejection


def test_rejection_is_raisable_and_carries_its_message() -> None:
    with pytest.raises(rejection.Rejection, match="denied"):
        raise rejection.Rejection("denied")


def test_rejection_is_an_exception() -> None:
    assert issubclass(rejection.Rejection, Exception)
