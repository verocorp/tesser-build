import typing

import tesser.application.factory as factory
import tesser.application.workflow as workflow


class _Built(typing.Protocol):
    def act(self) -> int: ...


@typing.runtime_checkable
class _Builds(factory.Factory, typing.Protocol):
    def __call__(self, seed: int, /) -> _Built: ...


class _Impl:

    def __init__(self, seed: int) -> None:
        self._seed = seed

    def act(self) -> int:
        return self._seed


def test_a_class_is_its_own_factory_without_inheritance() -> None:
    assert isinstance(_Impl, _Builds)
    assert factory.Factory not in _Impl.__mro__


def test_factory_is_a_protocol_base_that_extends_into_new_protocols() -> None:
    assert factory.Factory in _Builds.__mro__


def test_a_factory_is_not_a_workflow() -> None:
    assert workflow.Workflow not in factory.Factory.__mro__
    assert factory.Factory not in workflow.Workflow.__mro__


def test_factory_carries_no_behavior_of_its_own() -> None:
    own = {name for name in vars(factory.Factory) if not name.startswith("_")}
    assert own == set(), own
