from tesser.domain.spec import Spec


def test_spec_is_a_plain_marker_base() -> None:
    class Concrete(Spec):
        pass

    assert issubclass(Concrete, Spec)
    assert Spec.__mro__[1:] == (object,)
    assert not hasattr(Spec, "__slots__")


def test_spec_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Spec) if not name.startswith("__")}
    assert own == set(), own
