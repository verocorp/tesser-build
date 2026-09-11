import tesser.adapters.gateway as gateway
import tesser.adapters.runner as runner
import tesser.adapters.runtime as runtime


def test_runner_is_a_plain_marker_base() -> None:
    class Concrete(runner.Runner):
        pass

    assert issubclass(Concrete, runner.Runner)
    assert runner.Runner.__mro__[1:] == (object,)
    assert not hasattr(runner.Runner, "__slots__")


def test_a_runner_is_neither_a_gateway_nor_a_runtime() -> None:
    assert not issubclass(runner.Runner, gateway.Gateway)
    assert not issubclass(gateway.Gateway, runner.Runner)
    assert not issubclass(runner.Runner, runtime.Runtime)
    assert not issubclass(runtime.Runtime, runner.Runner)


def test_runner_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(runner.Runner) if not name.startswith("__")}
    assert own == set(), own
