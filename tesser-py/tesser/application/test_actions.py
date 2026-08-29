import tesser.application.actions as actions
import tesser.application.service as service


def test_actions_is_a_plain_marker_base() -> None:
    class Concrete(actions.Actions):
        pass

    assert issubclass(Concrete, actions.Actions)
    assert actions.Actions.__mro__[1:] == (object,)
    assert not hasattr(actions.Actions, "__slots__")


def test_actions_is_not_an_application_service() -> None:
    assert not issubclass(actions.Actions, service.ApplicationService)
    assert not issubclass(service.ApplicationService, actions.Actions)


def test_actions_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(actions.Actions) if not name.startswith("__")}
    assert own == set(), own
