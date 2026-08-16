import pytest

from tesser.srv.rejection import Rejection


def test_rejection_is_raisable_and_carries_its_message() -> None:
    with pytest.raises(Rejection, match="denied"):
        raise Rejection("denied")


def test_rejection_is_an_exception() -> None:
    assert issubclass(Rejection, Exception)
