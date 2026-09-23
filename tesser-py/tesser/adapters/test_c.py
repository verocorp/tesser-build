import tesser.adapters.c as c
import tesser.adapters.runtime as runtime


def test_c_is_a_plain_marker_base() -> None:
    class Concrete(c.C):
        pass

    assert issubclass(Concrete, c.C)
    assert c.C.__mro__[1:] == (object,)
    assert not hasattr(c.C, "__slots__")


def test_c_is_not_a_runtime() -> None:
    assert not issubclass(c.C, runtime.Runtime)
    assert not issubclass(runtime.Runtime, c.C)


def test_c_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(c.C) if not name.startswith("__")}
    assert own == set(), own
