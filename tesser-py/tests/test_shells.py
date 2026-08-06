from typing import Protocol

import tesser.adapters
import tesser.application
import tesser.context
import tesser.domain
import tesser.testing


class _AskThings(tesser.context.Client, Protocol):
    def ask(self, question: object) -> object: ...


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


def test_client_subclass_stays_a_protocol() -> None:
    assert getattr(_AskThings, "_is_protocol", False)
    assert tesser.context.Client in _AskThings.__mro__


def test_declaration_decorators_return_their_target_unchanged() -> None:
    def build() -> str:
        return "built"

    class Double:
        pass

    assert tesser.domain.function(build) is build
    assert tesser.application.function(build) is build
    assert tesser.adapters.function(build) is build
    assert tesser.context.function(build) is build
    assert tesser.testing.helper(build) is build
    assert tesser.testing.fake(Double) is Double


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

    class Wire(tesser.context.Wiring):
        pass

    class Inbound(tesser.adapters.Handler):
        pass

    for cls in (Root, RootSpec, Service, Repo, Ask, Reply, Wire, Inbound):
        assert cls()
