import tesser.app.spec as spec


def test_spec_is_a_plain_marker_base() -> None:
    class Concrete(spec.Spec):
        pass

    assert issubclass(Concrete, spec.Spec)
    assert spec.Spec.__mro__[1:] == (object,)


def test_spec_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(spec.Spec) if not name.startswith("__")}
    assert own == set(), own
