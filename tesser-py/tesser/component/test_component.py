import tesser.component.component as component


def test_component_is_a_plain_marker_base() -> None:
    class Concrete(component.Component):
        pass

    assert issubclass(Concrete, component.Component)
    assert component.Component.__mro__[1:] == (object,)


def test_component_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(component.Component) if not name.startswith("__")}
    assert own == set(), own
