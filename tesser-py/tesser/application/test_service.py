import tesser.application.service as service


def test_application_service_is_a_plain_marker_base() -> None:
    class Concrete(service.ApplicationService):
        pass

    assert issubclass(Concrete, service.ApplicationService)
    assert service.ApplicationService.__mro__[1:] == (object,)
    assert not hasattr(service.ApplicationService, "__slots__")


def test_application_service_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(service.ApplicationService) if not name.startswith("__")}
    assert own == set(), own
