import tesser.adapters.handler as handler


def test_handler_is_a_plain_marker_base() -> None:
    class Concrete(handler.Handler):
        pass

    assert issubclass(Concrete, handler.Handler)
    assert handler.Handler.__mro__[1:] == (object,)
    assert not hasattr(handler.Handler, "__slots__")


def test_handler_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(handler.Handler) if not name.startswith("__")}
    assert own == set(), own
