from tesser.application.service import ApplicationService


def test_application_service_is_a_plain_marker_base() -> None:
    class Concrete(ApplicationService):
        pass

    assert issubclass(Concrete, ApplicationService)
    assert ApplicationService.__mro__[1:] == (object,)
    assert not hasattr(ApplicationService, "__slots__")


def test_application_service_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(ApplicationService) if not name.startswith("__")}
    assert own == set(), own
