import tesser.adapters.handler as handler
import tesser.adapters.runtime as runtime


def test_runtime_is_a_plain_marker_base() -> None:
    class Concrete(runtime.Runtime):
        pass

    assert issubclass(Concrete, runtime.Runtime)
    assert runtime.Runtime.__mro__[1:] == (object,)
    assert not hasattr(runtime.Runtime, "__slots__")


def test_a_runtime_is_not_a_handler() -> None:
    assert not issubclass(runtime.Runtime, handler.Handler)
    assert not issubclass(handler.Handler, runtime.Runtime)


def test_runtime_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(runtime.Runtime) if not name.startswith("__")}
    assert own == set(), own
