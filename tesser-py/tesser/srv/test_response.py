from tesser.srv.response import Response
from tesser.srv.record import Record


def test_response_extends_record() -> None:
    assert issubclass(Response, Record)
    assert Record in Response.__mro__


def test_response_adds_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Response) if not name.startswith("__")}
    assert own == set(), own
