from tesser.context.request import Request


def test_request_is_a_plain_marker_base() -> None:
    class Concrete(Request):
        pass

    assert issubclass(Concrete, Request)
    assert Request.__mro__[1:] == (object,)
    assert not hasattr(Request, "__slots__")


def test_request_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Request) if not name.startswith("__")}
    assert own == set(), own
