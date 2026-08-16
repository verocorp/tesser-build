from tesser.context.wiring import Wiring


def test_wiring_is_a_plain_marker_base() -> None:
    class Concrete(Wiring):
        pass

    assert issubclass(Concrete, Wiring)
    assert Wiring.__mro__[1:] == (object,)
    assert not hasattr(Wiring, "__slots__")


def test_wiring_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Wiring) if not name.startswith("__")}
    assert own == set(), own
