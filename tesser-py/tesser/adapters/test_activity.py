import tesser.adapters.activity as activity
import tesser.adapters.runtime as runtime


def test_activity_is_a_plain_marker_base() -> None:
    class Concrete(activity.Activity):
        pass

    assert issubclass(Concrete, activity.Activity)
    assert activity.Activity.__mro__[1:] == (object,)
    assert not hasattr(activity.Activity, "__slots__")


def test_activity_is_not_a_runtime() -> None:
    assert not issubclass(activity.Activity, runtime.Runtime)
    assert not issubclass(runtime.Runtime, activity.Activity)


def test_activity_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(activity.Activity) if not name.startswith("__")}
    assert own == set(), own
