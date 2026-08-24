import tesser.context.request as request


def test_request_is_a_plain_marker_base() -> None:
    class Concrete(request.Request):
        pass

    assert issubclass(Concrete, request.Request)
    assert request.Request.__mro__[1:] == (object,)
    assert not hasattr(request.Request, "__slots__")


def test_request_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(request.Request) if not name.startswith("__")}
    assert own == set(), own
