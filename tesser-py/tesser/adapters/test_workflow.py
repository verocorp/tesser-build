import asyncio
import contextlib
import typing

import tesser.adapters.workflow as workflow


class _Context:
    pass


class _Orchestrator:

    def __init__(self, context: _Context) -> None:
        self.context = context


class _Impl:

    @contextlib.asynccontextmanager
    async def invocation(self, context: _Context) -> typing.AsyncIterator[_Orchestrator]:
        yield _Orchestrator(context)


def test_an_invocation_yields_what_it_built_from_the_context_it_was_handed() -> None:
    _impl: workflow.Workflow[_Context, _Orchestrator] = _Impl()

    assert isinstance(asyncio.run(_impl.invocation(_Context()).__aenter__()), _Orchestrator)


def test_workflow_is_satisfied_structurally_without_inheritance() -> None:
    assert workflow.Workflow not in type(_Impl()).__mro__


def test_workflow_carries_one_operation_and_nothing_else() -> None:
    own = {name for name in vars(workflow.Workflow) if not name.startswith("_")}
    assert own == {"invocation"}, own
