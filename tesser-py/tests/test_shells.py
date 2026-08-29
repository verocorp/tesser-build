import typing

import tesser.adapters
import tesser.application
import tesser.component
import tesser.context
import tesser.domain
import tesser.srv
import tesser.testing


class _AskThings(tesser.context.Client, typing.Protocol):
    def ask(self, question: object) -> object: ...


class _SaveThings(tesser.application.Port, typing.Protocol):
    def save(self, thing: object) -> None: ...


class _ServeThings(tesser.srv.Port, typing.Protocol):
    def __call__(self, request: object) -> object: ...


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


def test_srv_port_subclass_stays_a_protocol() -> None:
    assert getattr(_ServeThings, "_is_protocol", False)
    assert tesser.srv.Port in _ServeThings.__mro__


def test_srv_port_is_a_distinct_kind_from_the_application_port() -> None:
    assert tesser.srv.Port is not tesser.application.Port
    assert tesser.application.Port not in _ServeThings.__mro__


def test_application_client_is_a_distinct_kind_from_the_context_client() -> None:
    class _RunThings(tesser.application.Client, typing.Protocol):
        def run(self, request: object) -> object: ...

    application_client: object = tesser.application.Client
    assert application_client is not tesser.context.Client
    assert getattr(_RunThings, "_is_protocol", False)
    assert tesser.context.Client not in _RunThings.__mro__


def test_srv_records_are_distinct_kinds_from_the_context_dtos() -> None:
    class WireAsk(tesser.srv.Request):
        pass

    class WireReply(tesser.srv.Response):
        pass

    srv_request: object = tesser.srv.Request
    srv_response: object = tesser.srv.Response
    assert srv_request is not tesser.context.Request
    assert srv_response is not tesser.context.Response
    assert tesser.context.Request not in WireAsk.__mro__
    assert tesser.context.Response not in WireReply.__mro__


def test_declaration_decorators_return_their_target_unchanged() -> None:
    def build() -> str:
        return "built"

    class Double:
        pass

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

    class Wire(tesser.component.Component):
        pass

    class Inbound(tesser.adapters.Handler):
        pass

    class Server(tesser.srv.Host):
        pass

    class WireAsk(tesser.srv.Request):
        pass

    class WireReply(tesser.srv.Response):
        pass

    class Flow(tesser.application.Orchestrator):
        pass

    class Steps(tesser.application.Actions):
        pass

    class Work(tesser.adapters.Job):
        pass

    for cls in (
        Root, RootSpec, Service, Repo, Ask, Reply, Wire, Inbound, Server, WireAsk, WireReply, Flow, Steps, Work
    ):
        assert cls()
