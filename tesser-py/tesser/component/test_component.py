from tesser.component.component import Component


def test_component_is_a_plain_marker_base() -> None:
    class Concrete(Component):
        pass

    assert issubclass(Concrete, Component)
    assert Component.__mro__[1:] == (object,)


def test_component_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(Component) if not name.startswith("__")}
    assert own == set(), own
