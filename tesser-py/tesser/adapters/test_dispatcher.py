import tesser.adapters.dispatcher as dispatcher
import tesser.adapters.runtime as runtime


def test_dispatcher_is_a_plain_marker_base() -> None:
    class Concrete(dispatcher.Dispatcher):
        pass

    assert issubclass(Concrete, dispatcher.Dispatcher)
    assert dispatcher.Dispatcher.__mro__[1:] == (object,)
    assert not hasattr(dispatcher.Dispatcher, "__slots__")


def test_dispatcher_is_not_a_runtime() -> None:
    assert not issubclass(dispatcher.Dispatcher, runtime.Runtime)
    assert not issubclass(runtime.Runtime, dispatcher.Dispatcher)


def test_dispatcher_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(dispatcher.Dispatcher) if not name.startswith("__")}
    assert own == set(), own
