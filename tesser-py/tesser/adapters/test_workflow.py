import tesser.adapters.runtime as runtime
import tesser.adapters.workflow as workflow


def test_workflow_is_a_plain_marker_base() -> None:
    class Concrete(workflow.Workflow):
        pass

    assert issubclass(Concrete, workflow.Workflow)
    assert workflow.Workflow.__mro__[1:] == (object,)
    assert not hasattr(workflow.Workflow, "__slots__")


def test_workflow_is_not_a_runtime() -> None:
    assert not issubclass(workflow.Workflow, runtime.Runtime)
    assert not issubclass(runtime.Runtime, workflow.Workflow)


def test_workflow_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(workflow.Workflow) if not name.startswith("__")}
    assert own == set(), own
