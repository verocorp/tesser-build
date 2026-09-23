import tesser.adapters.b as b
import tesser.adapters.runtime as runtime


def test_b_is_a_plain_marker_base() -> None:
    class Concrete(b.B):
        pass

    assert issubclass(Concrete, b.B)
    assert b.B.__mro__[1:] == (object,)
    assert not hasattr(b.B, "__slots__")


def test_b_is_not_a_runtime() -> None:
    assert not issubclass(b.B, runtime.Runtime)
    assert not issubclass(runtime.Runtime, b.B)


def test_b_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(b.B) if not name.startswith("__")}
    assert own == set(), own
