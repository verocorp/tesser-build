import tesser.adapters.runtime as runtime
import tesser.adapters.signal as signal


def test_signal_is_a_plain_marker_base() -> None:
    class Concrete(signal.Signal):
        pass

    assert issubclass(Concrete, signal.Signal)
    assert signal.Signal.__mro__[1:] == (object,)
    assert not hasattr(signal.Signal, "__slots__")


def test_signal_is_not_a_runtime() -> None:
    assert not issubclass(signal.Signal, runtime.Runtime)
    assert not issubclass(runtime.Runtime, signal.Signal)


def test_signal_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(signal.Signal) if not name.startswith("__")}
    assert own == set(), own
