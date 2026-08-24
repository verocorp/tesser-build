import tesser.srv.response as response
import tesser.srv.record as record


def test_response_extends_record() -> None:
    assert issubclass(response.Response, record.Record)
    assert record.Record in response.Response.__mro__


def test_response_adds_no_behavior_of_its_own() -> None:
    own = {name for name in vars(response.Response) if not name.startswith("__")}
    assert own == set(), own
