from __future__ import annotations

from pathlib import Path

import pytest

import tesser.testing as ts

import tessercheck.domain.checks as checks


@ts.helper
def _spec(
    sources: tuple[tuple[str, str, str | None, bool], ...] = (),
    base: tuple[tuple[str, str, str | None, bool], ...] = (
        (
            "app/domain/thing.py",
            "app.domain.thing",
            "import tesser.domain as ts\n"
            "class ThingSpec(ts.Spec):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class Thing(ts.AggregateRoot):\n"
            "    def __init__(self, spec: ThingSpec) -> None:\n"
            "        self.text = spec.text\n",
            False,
        ),
        (
            "app/client/client.py",
            "app.client.client",
            "import tesser.context as ts\n"
            "class AskRequest(ts.Request):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class AskResponse(ts.Response):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n",
            False,
        ),
        (
            "app/application/service.py",
            "app.application.service",
            "import tesser.application as ts\n"
            "import app.client.client as client\n"
            "class AskService(ts.ApplicationService):\n"
            "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
            "        return client.AskResponse(text=request.text)\n"
            "    def _helper(self, anything: int) -> int:\n"
            "        return anything\n",
            False,
        ),
    ),
) -> checks.CodebaseSpec:
    return checks.CodebaseSpec(
        sources=base + sources, declared="app", nested=(), symlinked=()
    )


def test_every_declared_block_has_a_name_and_a_home() -> None:
    blocks = set(checks.TESSER_BASE_BLOCKS.values())
    assert set(checks.KIND_NAME) == blocks
    assert set(checks.KIND_ROLE) == blocks - checks.SRV_KINDS


def test_every_kind_row_names_a_real_tesser_export() -> None:
    root = Path(__file__).resolve().parents[3] / "tesser-py"
    rows = list(checks.TESSER_BASE_BLOCKS) + list(checks.TESSER_DECORATORS)
    for package, name in rows:
        exports = (root / package.replace(".", "/") / "__init__.py").read_text()
        assert f" {name} as {name}" in exports


def test_primitive_parameter_and_return_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/bad.py",
                "app.bad",
                "import tesser.application as ts\n"
                "class BadService(ts.ApplicationService):\n"
                "    def ask(self, text: str) -> str:\n"
                "        return text\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "parameter 'text' is not a ts.Request; a service method takes exactly one ts.Request"
        in f
        for f in findings
    )
    assert any(
        "does not return a ts.Response; a service method returns a ts.Response" in f
        for f in findings
    )


def test_arity_and_missing_annotations_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/bad.py",
                "app.bad",
                "import tesser.application as ts\n"
                "from app.client.client import AskRequest, AskResponse\n"
                "class BadService(ts.ApplicationService):\n"
                "    def two(self, a: AskRequest, b: AskRequest) -> AskResponse:\n"
                "        return AskResponse(text='')\n"
                "    def bare(self, request) -> AskResponse:\n"
                "        return AskResponse(text='')\n"
                "    def spread(self, *args: object) -> AskResponse:\n"
                "        return AskResponse(text='')\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "takes 2 parameters; a service method takes exactly one ts.Request" in f
        for f in findings
    )
    assert any(
        "parameter 'request' is not a ts.Request; a service method takes exactly one ts.Request"
        in f
        for f in findings
    )
    assert any(
        "uses *args/**kwargs; a service method takes exactly one ts.Request" in f
        for f in findings
    )


def test_aggregate_constructor_violations_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/badroots.py",
                "app.badroots",
                "import tesser.domain as ts\n"
                "from app.domain.thing import ThingSpec\n"
                "class Primitive(ts.AggregateRoot):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class Two(ts.AggregateRoot):\n"
                "    def __init__(self, a: ThingSpec, b: ThingSpec) -> None:\n"
                "        self.a = a\n"
                "class NoConstructor(ts.AggregateRoot):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "Primitive.__init__" in f
        and "parameter 'text' is not a ts.Spec; a domain constructor takes exactly one ts.Spec"
        in f
        for f in findings
    )
    assert any(
        "Two.__init__" in f
        and "takes 2 parameters; a domain constructor takes exactly one ts.Spec" in f
        for f in findings
    )
    assert any(
        "NoConstructor" in f
        and "defines no __init__; an aggregate constructs from exactly one ts.Spec" in f
        for f in findings
    )


def test_service_body_rules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/busy.py",
                "app.busy",
                "import tesser.application as ts\n"
                "from app.client.client import AskRequest, AskResponse\n"
                "class BusyService(ts.ApplicationService):\n"
                "    def long(self, request: AskRequest) -> AskResponse:\n"
                + "".join(f"        step_{i} = request.text\n" for i in range(11))
                + "        return AskResponse(text=step_0)\n"
                "    def nested(self, request: AskRequest) -> AskResponse:\n"
                "        if request.ping():\n"
                "            if request.pong():\n"
                "                return AskResponse(text='')\n"
                "        return AskResponse(text='')\n"
                "    def compares(self, request: AskRequest) -> AskResponse:\n"
                "        if request.text == 'x':\n"
                "            return AskResponse(text='')\n"
                "        return AskResponse(text='')\n"
                "    def combines(self, request: AskRequest) -> AskResponse:\n"
                "        if request.ready() and request.good():\n"
                "            return AskResponse(text='')\n"
                "        return AskResponse(text='')\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "BusyService.long" in f
        and "body spans 12 source lines; a service method body is at most 10 source lines"
        in f
        for f in findings
    )
    assert any(
        "BusyService.nested" in f
        and "nests a conditional" in f
        and "a service method branches one level deep" in f
        for f in findings
    )
    assert any(
        "BusyService.compares" in f
        and "is not a single call; a service method satisfies a condition with one domain call"
        in f
        for f in findings
    )
    assert any(
        "BusyService.combines" in f
        and "is not a single call; a service method satisfies a condition with one domain call"
        in f
        for f in findings
    )


def test_service_delegation_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/helped.py",
                "app.helped",
                "import tesser.application as ts\n"
                "from app.client.client import AskRequest, AskResponse\n"
                "def shape(text: str) -> str:\n"
                "    return text\n"
                "class HelpedService(ts.ApplicationService):\n"
                "    def ask(self, request: AskRequest) -> AskResponse:\n"
                "        return self._prep(request)\n"
                "    def _prep(self, request: AskRequest) -> AskResponse:\n"
                "        return AskResponse(text=shape(request.text))\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "HelpedService.ask" in f
        and "delegates to self._prep" in f
        and "a service inlines its logic" in f
        for f in findings
    )
    assert any(
        "HelpedService._prep" in f
        and "delegates to shape" in f
        and "a service inlines its logic" in f
        for f in findings
    )


def test_elif_chain_is_one_level() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/chained.py",
                "app.chained",
                "import tesser.application as ts\n"
                "from app.client.client import AskRequest, AskResponse\n"
                "class ChainService(ts.ApplicationService):\n"
                "    def pick(self, request: AskRequest) -> AskResponse:\n"
                "        if request.ready():\n"
                "            return AskResponse(text='a')\n"
                "        elif request.good():\n"
                "            return AskResponse(text='b')\n"
                "        return AskResponse(text='c')\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "ChainService" in f and "a service method branches one level deep" in f
        for f in findings
    )


def test_indirect_subclass_still_classifies() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/derived.py",
                "app.derived",
                "from app.application.service import AskService\n"
                "from app.client.client import AskRequest\n"
                "class DerivedService(AskService):\n"
                "    def again(self, request: AskRequest) -> AskRequest:\n"
                "        return request\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "DerivedService.again" in f
        and "does not return a ts.Response; a service method returns a ts.Response" in f
        for f in findings
    )


def test_service_dependencies_must_be_ports() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/extra.py",
                "app.extra",
                "import tesser.application as ts\n"
                "from app.client.client import AskRequest, AskResponse\n"
                "class NeedyService(ts.ApplicationService):\n"
                "    def __init__(self, db: str) -> None:\n"
                "        self._db = db\n"
                "    def ask(self, request: AskRequest) -> AskResponse:\n"
                "        return AskResponse(text=request.text)\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "NeedyService.__init__" in f
        and "parameter 'db' is not a ts.Port; a service depends only on ports" in f
        for f in findings
    )


def test_client_method_rules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/extra2.py",
                "app.extra2",
                "from typing import Protocol\n"
                "import tesser.context as tc\n"
                "class BadClient(tc.Client, Protocol):\n"
                "    def ask(self, text: str) -> str: ...\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "BadClient.ask" in f
        and "parameter 'text' is not a ts.Request; a client method takes exactly one ts.Request"
        in f
        for f in findings
    )
    assert any(
        "BadClient.ask" in f
        and "does not return a ts.Response; a client method returns a ts.Response" in f
        for f in findings
    )


def test_records_never_carry_domain_objects() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/extra3.py",
                "app.extra3",
                "from typing import Protocol\n"
                "import tesser.adapters as ta\n"
                "import tesser.application as tap\n"
                "from app.domain.thing import Thing\n"
                "class LoadingRepo(ta.Repository):\n"
                "    def load(self, key: str) -> Thing: ...\n"
                "class LoadingPort(tap.Port, Protocol):\n"
                "    def fetch(self) -> Thing: ...\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "LoadingRepo.load" in f and "an adapter speaks records, never domain objects" in f
        for f in findings
    )
    assert any(
        "LoadingPort.fetch" in f and "a port speaks records, never domain objects" in f
        for f in findings
    )


def test_domain_field_rules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/extra4.py",
                "app.extra4",
                "import tesser.domain as ts\n"
                "import tesser.context as tc\n"
                "class Money(ts.ValueObject):\n"
                "    def __init__(self, amounts: dict) -> None:\n"
                "        object.__setattr__(self, '_amounts', amounts)\n"
                "class BagSpec(ts.Spec):\n"
                "    def __init__(self, mapping: dict) -> None:\n"
                "        self.mapping = mapping\n"
                "    def polish(self) -> None:\n"
                "        return None\n"
                "class Item(ts.Entity):\n"
                "    pass\n"
                "class WireRequest(tc.Request):\n"
                "    def __init__(self, items: list) -> None:\n"
                "        self.items = items\n"
                "    def validate(self) -> None:\n"
                "        return None\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "Money.__init__" in f
        and "a value object constructs from primitives and value objects" in f
        for f in findings
    )
    assert any(
        "BagSpec.__init__" in f
        and "a spec field is a primitive, a value object, or a child spec" in f
        for f in findings
    )
    assert any(
        "BagSpec.polish" in f and "a spec only carries construction data" in f
        for f in findings
    )
    assert any(
        "Item" in f and "an entity constructs from exactly one ts.Spec" in f
        for f in findings
    )
    assert any(
        "WireRequest.__init__" in f and "a DTO field is a primitive or another DTO" in f
        for f in findings
    )
    assert any(
        "WireRequest.validate" in f and "a DTO carries data and nothing else" in f
        for f in findings
    )


def test_edge_records_reject_an_empty_target() -> None:
    with pytest.raises(ValueError):
        checks.ImportEdge("", 1, False, False)
    with pytest.raises(ValueError):
        checks.TesserImport("", 1, False, False)


def test_optional_construction_data_is_the_only_union() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/opt.py",
                "app.domain.opt",
                "import tesser.domain as ts\n"
                "class OptSpec(ts.Spec):\n"
                "    def __init__(self, text: str | None, items: list | None, mix: str | int) -> None:\n"
                "        self.text = text\n"
                "        self.items = items\n"
                "        self.mix = mix\n",
                False,
            ),
        ))).violations()
               )
    assert not any("parameter 'text'" in f for f in findings)
    assert any(
        "parameter 'items' is not allowed; "
        "a spec field is a primitive, a value object, or a child spec" in f
        for f in findings
    )
    assert any("parameter 'mix' is not allowed" in f for f in findings)


def test_bytes_is_construction_primitive() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/digest.py",
                "app.domain.digest",
                "import tesser.domain as ts\n"
                "class Digest(ts.ValueObject):\n"
                "    _value: bytes\n"
                "    def __init__(self, value: bytes) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __bytes__(self) -> bytes:\n"
                "        return self._value\n",
                False,
            ),
        ))).violations()
               )
    assert not any("parameter 'value' is not allowed" in f for f in findings)


def test_async_def_is_not_a_way_around_a_method_rule() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/client/async_client.py",
                "app.client.async_client",
                "from __future__ import annotations\n"
                "from typing import Protocol\n"
                "import tesser.context as ts\n"
                "class Ask(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Loose(ts.Client, Protocol):\n"
                "    async def ask(self, id: str, extra: int) -> str: ...\n",
                False,
            ),
            (
                "app/adapters/gateways/async_repo.py",
                "app.adapters.gateways.async_repo",
                "from __future__ import annotations\n"
                "import tesser.adapters as ts\n"
                "import app.domain.thing as thing\n"
                "class Loose(ts.Repository):\n"
                "    async def save(self, entity: thing.Thing) -> None: ...\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.client.async_client.Loose.ask" in f
        and "a client method takes exactly one" in f
        for f in findings
    ), f"an async client method escaped the client shape rule: {findings}"
    assert any(
        "app.adapters.gateways.async_repo.Loose.save carries an aggregate in its signature"
        in f
        for f in findings
    ), f"an async adapter method escaped the record rule: {findings}"


def test_an_adapters_module_holds_one_kind() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n"
                "class SideGateway(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.adapters.gateways mixes adapter kinds" in f
        and "an adapters module holds one adapter kind" in f
        for f in findings
    )


def test_a_dotted_module_base_resolves() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_doubles.py",
                "app.test_doubles",
                "import tesser.testing as th\n"
                "import app.application.service\n"
                "@th.fake\n"
                "class FakePort(app.application.service.AskService):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "FakePort" in f and "implements no ts.Port" in f and "undeclared" in f
        for f in findings
    )
    assert any(
        "FakePort" in f and "a fake implements the port or client it doubles" in f
        for f in findings
    )
