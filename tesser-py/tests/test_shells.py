from typing import Protocol

import tesser.adapters
import tesser.application
import tesser.context
import tesser.domain


class _SaveThings(tesser.application.Port, Protocol):
    def save(self, thing: object) -> None: ...


class _StructuralSaver:
    def __init__(self) -> None:
        self.saved: list[object] = []

    def save(self, thing: object) -> None:
        self.saved.append(thing)


def test_aggregate_root_is_an_entity() -> None:
    assert issubclass(tesser.domain.AggregateRoot, tesser.domain.Entity)


def test_port_subclass_stays_a_protocol() -> None:
    assert getattr(_SaveThings, "_is_protocol", False)
    assert tesser.application.Port in _SaveThings.__mro__


def test_structural_implementation_needs_no_marker() -> None:
    saver: _SaveThings = _StructuralSaver()
    saver.save("x")
    assert tesser.application.Port not in type(saver).__mro__


def test_shells_classify_subclasses() -> None:
    class Root(tesser.domain.AggregateRoot):
        pass

    class RootSpec(tesser.domain.Spec):
        pass

    class Service(tesser.application.ApplicationService):
        pass

    class Repo(tesser.adapters.Repository):
        pass

    class Ask(tesser.context.Request):
        pass

    class Reply(tesser.context.Response):
        pass

    for cls in (Root, RootSpec, Service, Repo, Ask, Reply):
        assert cls()
