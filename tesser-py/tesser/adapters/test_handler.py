from tesser.adapters.handler import Handler


def test_handler_is_a_plain_marker_base() -> None:
    class Concrete(Handler):
        pass

    assert issubclass(Concrete, Handler)
    assert Handler.__mro__[1:] == (object,)
    assert not hasattr(Handler, "__slots__")


def test_handler_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Handler) if not name.startswith("__")}
    assert own == set(), own
