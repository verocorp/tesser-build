import tesser.srv.request as request
import tesser.srv.record as record


def test_request_extends_record() -> None:
    assert issubclass(request.Request, record.Record)
    assert record.Record in request.Request.__mro__


def test_request_adds_no_behavior_of_its_own() -> None:
    own = {name for name in vars(request.Request) if not name.startswith("__")}
    assert own == set(), own
