import tesser.adapters.a as a
import tesser.adapters.runtime as runtime


def test_a_is_a_plain_marker_base() -> None:
    class Concrete(a.A):
        pass

    assert issubclass(Concrete, a.A)
    assert a.A.__mro__[1:] == (object,)
    assert not hasattr(a.A, "__slots__")


def test_a_is_not_a_runtime() -> None:
    assert not issubclass(a.A, runtime.Runtime)
    assert not issubclass(runtime.Runtime, a.A)


def test_a_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(a.A) if not name.startswith("__")}
    assert own == set(), own
