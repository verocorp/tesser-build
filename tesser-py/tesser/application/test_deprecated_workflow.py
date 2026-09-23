import contextlib
import typing

import tesser.application.deprecated_workflow as deprecated_workflow
import tesser.application.store as store


class _Held(typing.Protocol):
    def act(self) -> int: ...


class _HeldImpl:

    def act(self) -> int:
        return 1


@typing.runtime_checkable
class _Opens[C](deprecated_workflow.DeprecatedWorkflow, typing.Protocol):
    def invocation(self, context: C, /) -> typing.AsyncContextManager[_Held]: ...


class _Impl:

    @contextlib.asynccontextmanager
    async def invocation(self, context: int) -> typing.AsyncIterator[_HeldImpl]:
        yield _HeldImpl()


def test_deprecated_workflow_is_satisfied_structurally_without_inheritance() -> None:
    assert isinstance(_Impl(), _Opens)
    assert deprecated_workflow.DeprecatedWorkflow not in type(_Impl()).__mro__


def test_deprecated_workflow_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert deprecated_workflow.DeprecatedWorkflow in _Opens.__mro__


def test_a_deprecated_workflow_is_not_a_store() -> None:
    assert store.Store not in deprecated_workflow.DeprecatedWorkflow.__mro__
    assert deprecated_workflow.DeprecatedWorkflow not in store.Store.__mro__


def test_deprecated_workflow_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(deprecated_workflow.DeprecatedWorkflow) if not name.startswith("_")}
    assert own == set(), own
