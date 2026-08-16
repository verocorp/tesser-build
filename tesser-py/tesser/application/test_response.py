from tesser.application.response import Response


def test_response_is_a_plain_marker_base() -> None:
    class Concrete(Response):
        pass

    assert issubclass(Concrete, Response)
    assert Response.__mro__[1:] == (object,)
    assert not hasattr(Response, "__slots__")


def test_response_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Response) if not name.startswith("__")}
    assert own == set(), own
