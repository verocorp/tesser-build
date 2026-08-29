import tesser.application.orchestrator as orchestrator
import tesser.application.service as service


def test_orchestrator_is_a_plain_marker_base() -> None:
    class Concrete(orchestrator.Orchestrator):
        pass

    assert issubclass(Concrete, orchestrator.Orchestrator)
    assert orchestrator.Orchestrator.__mro__[1:] == (object,)
    assert not hasattr(orchestrator.Orchestrator, "__slots__")


def test_orchestrator_is_not_an_application_service() -> None:
    assert not issubclass(orchestrator.Orchestrator, service.ApplicationService)
    assert not issubclass(service.ApplicationService, orchestrator.Orchestrator)


def test_orchestrator_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(orchestrator.Orchestrator) if not name.startswith("__")}
    assert own == set(), own
