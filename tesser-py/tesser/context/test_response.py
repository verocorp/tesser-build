import tesser.context.response as response


def test_response_is_a_plain_marker_base() -> None:
    class Concrete(response.Response):
        pass

    assert issubclass(Concrete, response.Response)
    assert response.Response.__mro__[1:] == (object,)
    assert not hasattr(response.Response, "__slots__")


def test_response_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(response.Response) if not name.startswith("__")}
    assert own == set(), own
