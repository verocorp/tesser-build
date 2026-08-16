from tesser.srv.request import Request
from tesser.srv.record import Record


def test_request_extends_record() -> None:
    assert issubclass(Request, Record)
    assert Record in Request.__mro__


def test_request_adds_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Request) if not name.startswith("__")}
    assert own == set(), own
