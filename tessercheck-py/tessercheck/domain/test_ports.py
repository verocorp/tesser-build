from __future__ import annotations

import tesser.testing as ts

import tessercheck.domain.checks as checks

@ts.helper
def _conforming() -> tuple[tuple[str, str, str, bool], ...]:  # tessercheck:ignore TB073
    return (
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
    )


@ts.helper
def _findings(  # tessercheck:ignore TB073
    sources: tuple[tuple[str, str, str, bool], ...] = (),
    conforming: bool = True,
) -> tuple[str, ...]:
    spec = checks.CodebaseSpec(
        sources=(_conforming() + sources) if conforming else sources,
        declared="app",
        nested=(),
        symlinked=(),
    )
    return tuple(
        f"{violation.path()}:{int(violation.line())}: "
        f"{violation.code()} {violation.text()}"
        for violation in checks.Codebase(spec).violations()
    )


def test_ports_is_a_package_never_a_module() -> None:
    findings = _findings(
        (
            (
                "app/application/ports.py",
                "app.application.ports",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports is a ports module; ports is a package, never a module" in f
        for f in findings
    )


def test_a_ports_init_is_empty() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "X = 1\n",
                True,
            ),
        )
    )
    assert any(
        "app.application.ports __init__ declares code; a ports __init__ is empty" in f
        for f in findings
    )


def test_a_ports_module_is_a_leaf() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/other.py",
                "app.application.ports.other",
                "import tesser.application as ts\n"
                "class OtherSink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\n"
                "import app.domain.thing as thing\n"
                "import app.application.ports.other as other\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink imports app.domain.thing; a ports module is a leaf "
        "and imports nothing from its tree, its own siblings included" in f
        for f in findings
    )
    assert any(
        "app.application.ports.sink imports app.application.ports.other; a ports module is a leaf "
        "and imports nothing from its tree, its own siblings included" in f
        for f in findings
    )


def test_a_ports_module_stdlib_allowlist() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import enum\n"
                "import socket\n"
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink imports socket; a ports module imports "
        "only tesser.application and the pure stdlib" in f
        for f in findings
    )
    assert not any("imports enum;" in f for f in findings)


def test_a_ports_module_tesser_import_rules() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.domain as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "app/application/ports/plain.py",
                "app.application.ports.plain",
                "import tesser.application\n"
                "class Plain(tesser.application.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink imports tesser.domain; "
        "a ports module imports only tesser.application" in f
        for f in findings
    )
    assert any(
        "a ports module imports tesser.application exactly once, as ts" in f for f in findings
    )


def test_a_ports_module_holds_only_imports_and_classes() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\n"
                "FOUND = 'found'\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink has a loose module-level statement; "
        "a ports module holds only imports and classes" in f
        for f in findings
    )


def test_a_ports_module_declares_exactly_one_port() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/two.py",
                "app.application.ports.two",
                "import tesser.application as ts\n"
                "class First(ts.Port):\n"
                "    pass\n"
                "class Second(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "app/application/ports/none.py",
                "app.application.ports.none",
                "import tesser.application as ts\n"
                "class Stray(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.two declares 2 ports; a ports module "
        "declares exactly one port, so no two ports can share a request or a response" in f
        for f in findings
    )
    assert any(
        "app.application.ports.none declares no port; a ports module "
        "declares exactly one port, so no two ports can share a request or a response" in f
        for f in findings
    )


def test_a_ports_module_holds_only_port_kinds() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\n"
                "class Bare:\n"
                "    pass\n"
                "class Leaked(ts.ApplicationService):\n"
                "    pass\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Bare declares no ts.* base; a ports class declares its block" in f
        for f in findings
    )
    assert any(
        "app.application.ports.sink.Leaked is a service; only a port and the requests "
        "and responses it speaks live in a ports module" in f
        for f in findings
    )


def test_a_port_method_speaks_one_request_and_one_response() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port):\n"
                "    def save(self, text: str) -> SaveResponse: ...\n"
                "    def load(self, request: SaveRequest) -> str: ...\n"
                "    def both(self, request: SaveRequest, extra: str) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Sink.save parameter 'text' is not a ts.Request; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    )
    assert any(
        "app.application.ports.sink.Sink.load does not return a ts.Response; "
        "a port method returns a ts.Response" in f
        for f in findings
    )
    assert any(
        "app.application.ports.sink.Sink.both takes 2 parameters; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    )


def test_an_adapter_reaches_application_only_through_ports() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "app/adapters/gateways/memory.py",
                "app.adapters.gateways.memory",
                "import tesser.adapters as ts\n"
                "import app.application.ports.sink as sink\n"
                "import app.application.service as service\n"
                "class MemorySink(ts.Repository):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.adapters.gateways.memory imports app.application.service; "
        "the same-context matrix is a role to itself, application to domain and client, "
        "adapters to application/ports, wiring to application, adapters, and client" in f
        for f in findings
    )
    assert not any("imports app.application.ports.sink;" in f for f in findings)


def test_a_port_dto_field_is_never_a_union() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class ItemView(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class FindResponse(ts.Response):\n"
                "    def __init__(self, item: ItemView | None) -> None:\n"
                "        self.item = item\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.FindResponse.__init__ field 'item' is a union; "
        "a port DTO field is never a union, optional included — model the outcome as an enum" in f
        for f in findings
    )


def test_a_client_dto_field_may_still_be_optional() -> None:
    findings = _findings(
        (
            (
                "app/client/optional.py",
                "app.client.optional",
                "from __future__ import annotations\n"
                "import tesser.context as ts\n"
                "class Inner(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Outer(ts.Response):\n"
                "    def __init__(self, inner: Inner | None) -> None:\n"
                "        self.inner = inner\n",
                False,
            ),
        )
    )
    assert not any("app.client.optional" in f and "is a union" in f for f in findings)


def test_a_conforming_ports_module_is_silent() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class Outcome(enum.Enum):\n"
                "    STORED = 'stored'\n"
                "    REFUSED = 'refused'\n"
                "class ItemView(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self, outcome: Outcome, items: tuple[ItemView, ...]) -> None:\n"
                "        self.outcome = outcome\n"
                "        self.items = items\n"
                "class ListRequest(ts.Request):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def save(self, request: SaveRequest) -> SaveResponse: ...\n"
                "    def all(self, request: ListRequest) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert not any("app/application/ports/sink.py" in f for f in findings), (
        f"a conforming ports module produced findings: "
        f"{[f for f in findings if 'ports/sink.py' in f]}"
    )


def test_a_ports_package_holds_only_ports_modules() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "app/application/ports/test_support.py",
                "app.application.ports.test_support",
                "import tesser.testing as ts\n"
                "import app.application.ports.sink as sink\n"
                "@ts.fake\n"
                "class Lookup(sink.Sink):\n"
                "    pass\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "app/application/ports/conftest.py",
                "app.application.ports.conftest",
                "",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.test_support is not a ports module; a ports package holds "
        "only ports modules, and test_/eval_/conftest are reserved names, because a fake "
        "here would be an implementation adapters may import" in f
        for f in findings
    ), f"a fake could live in the package adapters may import: {findings}"
    assert any("app.application.ports.conftest is not a ports module" in f for f in findings)


def test_a_client_dto_with_a_sibling_enum_stays_strict() -> None:
    findings = _findings(
        (
            (
                "app/client/verdict.py",
                "app.client.verdict",
                "from __future__ import annotations\n"
                "import tesser.context as ts\n"
                "class Verdict:\n"
                "    pass\n"
                "class VerdictResponse(ts.Response):\n"
                "    def __init__(self, verdict: Verdict) -> None:\n"
                "        self.verdict = verdict\n",
                False,
            ),
        )
    )
    assert any(
        "app.client.verdict.VerdictResponse.__init__ parameter 'verdict' is not allowed; "
        "a DTO field is a primitive or another DTO" in f
        for f in findings
    )


def test_a_port_dto_field_is_never_a_bare_bool() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "import tesser.application as ts\n"
                "class Outcome(enum.Enum):\n"
                "    YES = 'yes'\n"
                "    NO = 'no'\n"
                "class FlagResponse(ts.Response):\n"
                "    def __init__(self, found: bool, outcome: Outcome) -> None:\n"
                "        self.found = found\n"
                "        self.outcome = outcome\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.FlagResponse.__init__ field 'found' is a bool; "
        "a port DTO field is never a bare bool — model the outcome as an enum" in f
        for f in findings
    )
    assert not any("'outcome'" in f for f in findings)


def test_a_port_dto_is_never_subclassed() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class FindResponse(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class FoundItem(FindResponse):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.FoundItem subclasses a port DTO; a port DTO is never "
        "subclassed, because a response hierarchy is a union mypy cannot check for exhaustiveness" in f
        for f in findings
    )


def test_a_port_method_shape_survives_async_and_dunder_call() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    async def fetch(self, name: str, count: int) -> bool: ...\n"
                "    def __call__(self, name: str) -> bool: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Sink.fetch takes 2 parameters; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    ), f"async def bypassed the port shape rule: {findings}"
    assert any(
        "app.application.ports.sink.Sink.__call__ parameter 'name' is not a ts.Request" in f
        for f in findings
    ), f"__call__ bypassed the port shape rule: {findings}"


def test_a_fake_implementing_a_port_may_expose_inspection_methods() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
            (
                "app/application/test_sink.py",
                "app.application.test_sink",
                "import tesser.testing as ts\n"
                "import app.application.ports.sink as sink\n"
                "@ts.fake\n"
                "class FakeSink(sink.Sink):\n"
                "    def __init__(self) -> None:\n"
                "        self.saves = 0\n"
                "    def save(self, request: sink.SaveRequest) -> sink.SaveResponse:\n"
                "        self.saves = self.saves + 1\n"
                "        return sink.SaveResponse()\n"
                "    def save_count(self) -> int:\n"
                "        return self.saves\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
        )
    )
    assert not any("save_count" in f for f in findings), (
        f"a fake's inspection method was flagged as a port method: "
        f"{[f for f in findings if 'save_count' in f]}"
    )


def test_a_ports_enum_is_a_plain_enum() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "import tesser.application as ts\n"
                "class Loose(enum.StrEnum):\n"
                "    YES = 'yes'\n"
                "class Tight(enum.Enum):\n"
                "    YES = 'yes'\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Loose is an enum.StrEnum; a ports enum is an enum.Enum, "
        "because a str- or int-backed member compares equal to a raw literal "
        "and reopens the typo the enum closes" in f
        for f in findings
    )
    assert not any("Tight" in f for f in findings)


def test_a_port_method_declares_a_shape_and_never_a_body() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def save(self, request: SaveRequest) -> SaveResponse:\n"
                "        return SaveResponse()\n"
                "    def drop(self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Sink.save carries a body; a port method declares a shape "
        "and never a body, because a ports module holds no logic to import" in f
        for f in findings
    )
    assert not any("Sink.drop" in f for f in findings)


def test_an_ignored_ports_file_is_still_governed() -> None:
    findings = _findings(
        (
            (
                "app/application/ports.py",
                "app.application.ports",
                "import subprocess  # tessercheck:ignore TB067\n"
                "import tesser.application as ts  # tessercheck:ignore-file TB041\n"
                "import app.domain.thing as thing\n"
                "class First(ts.Port):\n"
                "    pass\n"
                "class Second(ts.Port):\n"
                "    pass\n"
                "class Leaked(ts.ApplicationService):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports imports app.domain.thing; a ports module is a leaf" in f
        for f in findings
    ), f"an ignored TB041 unlocked the module: {findings}"
    assert any("declares 2 ports" in f for f in findings)
    assert any("app.application.ports.Leaked is a service" in f for f in findings)


def test_an_enum_base_cannot_hide_a_second_port() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "import tesser.application as ts\n"
                "class First(ts.Port):\n"
                "    pass\n"
                "class Second(ts.Port, enum.auto):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any("declares 2 ports" in f for f in findings), (
        f"an enum base hid a second port, so two ports could share every DTO: {findings}"
    )


def test_an_enum_is_resolved_by_its_binding_not_its_spelling() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/masked.py",
                "app.application.ports.masked",
                "from __future__ import annotations\n"
                "import typing as enum\n"
                "import tesser.application as ts\n"
                "class Rules(enum.Any):\n"
                "    pass\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "app/application/ports/aliased.py",
                "app.application.ports.aliased",
                "from __future__ import annotations\n"
                "import enum as e\n"
                "import tesser.application as ts\n"
                "class Outcome(e.Enum):\n"
                "    YES = 'yes'\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.masked.Rules declares no ts.* base" in f for f in findings
    ), f"a name bound to something else was accepted as an enum: {findings}"
    assert not any("aliased.Outcome" in f for f in findings), (
        f"a properly bound enum alias was rejected: {findings}"
    )


def test_a_dynamic_import_is_not_a_way_around_the_matrix() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "app/adapters/gateways/memory.py",
                "app.adapters.gateways.memory",
                "import importlib\n"
                "import tesser.adapters as ts\n"
                "import app.application.ports.sink as sink\n"
                "class MemorySink(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self._service = importlib.import_module('app.application.service')\n",
                False,
            ),
        )
    )
    assert any(
        "app.adapters.gateways.memory imports dynamically through importlib.import_module; "
        "an import is a statement the walk can read, never a call" in f
        for f in findings
    ), f"importlib walked around the import matrix: {findings}"


def test_a_dto_declares_its_fields_where_the_rules_can_read_them() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class ClassLevel(ts.Response):\n"
                "    flag = False\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Splatted(ts.Response):\n"
                "    def __init__(self, **fields: object) -> None:\n"
                "        self.fields = fields\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.ClassLevel carries a class-level statement; a port DTO "
        "declares its fields as __init__ parameters, where the field rules can read them" in f
        for f in findings
    ), f"a class-level bool field walked around the bare-bool rule: {findings}"
    assert any(
        "app.application.ports.sink.Splatted.__init__ uses *args/**kwargs; a DTO declares "
        "its fields as named __init__ parameters, where the field rules can read them" in f
        for f in findings
    ), f"**kwargs walked around every DTO field rule: {findings}"


def test_an_async_method_on_a_dto_is_still_a_method() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class Loaded(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "    async def resolve(self) -> str:\n"
                "        return self.id\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Loaded.resolve defines a method on a DTO; "
        "a DTO carries data and nothing else" in f
        for f in findings
    ), f"async def carried logic onto a DTO: {findings}"


def test_a_nested_class_cannot_hide_a_second_port() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class First(ts.Port):\n"
                "    pass\n"
                "class Holder(ts.Response):\n"
                "    class Second(ts.Port):\n"
                "        pass\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Holder.Second is a nested class; a ports module declares "
        "its port and its DTOs at module level, where the one-port count can see them" in f
        for f in findings
    ), f"a nested class hid a second port sharing every DTO: {findings}"


def test_a_dynamic_import_is_resolved_by_binding_not_spelling() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
                False,
            ),
            (
                "app/adapters/gateways/memory.py",
                "app.adapters.gateways.memory",
                "from importlib import import_module\n"
                "import tesser.adapters as ts\n"
                "import app.application.ports.sink as sink\n"
                "class MemorySink(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self._service = import_module('app.application.service')\n",
                False,
            ),
            (
                "app/adapters/gateways/local.py",
                "app.adapters.gateways.local",
                "import tesser.adapters as ts\n"
                "import app.application.ports.sink as sink\n"
                "class LocalSink(ts.Repository):\n"
                "    def __init__(self, importlib: object) -> None:\n"
                "        self._loader = importlib\n",
                False,
            ),
        )
    )
    assert any(
        "app.adapters.gateways.memory imports dynamically through importlib.import_module" in f
        for f in findings
    ), f"a from-import of import_module walked around TB068: {findings}"
    assert not any("local" in f and "TB068" in f for f in findings), (
        f"a local name spelled importlib false-positived: {findings}"
    )


def test_a_port_speaks_shapes_it_declares_itself() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def bare(self, request: ts.Request) -> ts.Response: ...\n"
                "    def own(self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Sink.bare names a shape it does not declare; a port "
        "method speaks requests and responses declared in its own ports module, never a "
        "bare ts.Request or ts.Response, which two ports would share" in f
        for f in findings
    ), f"two ports could share the base classes as their whole vocabulary: {findings}"
    assert not any("Sink.own" in f for f in findings)


def test_a_ports_class_carries_no_class_level_statement() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class Outcome(enum.Enum):\n"
                "    YES = 'yes'\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    RESERVED = tuple(sorted({'admin'}))\n"
                "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Sink carries a class-level statement; only an enum "
        "member is class-level data in a ports module, because anything else runs at "
        "import in the one application module adapters may import" in f
        for f in findings
    ), f"import-time execution landed in the ports leaf: {findings}"
    assert not any("Outcome" in f for f in findings), f"an enum member was flagged: {findings}"


def test_a_private_port_method_carries_no_body() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def _score(self, name: str) -> int:\n"
                "        return len(name)\n"
                "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Sink._score carries a body; a port method declares a "
        "shape and never a body" in f
        for f in findings
    ), f"a private method carried logic every implementer inherits: {findings}"


def test_a_stub_cannot_shadow_the_shape_the_rules_read() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
                False,
            ),
            (
                "app/application/ports/sink.pyi",
                "app.application.ports.sink",
                "import tesser.application as ts\n"
                "class Loose(ts.Response):\n"
                "    allowed: bool\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink is a stub; a module carries its own shape, because a "
        "stub is what the type checker reads and the walk cannot" in f
        for f in findings
    ), f"a stub bypassed every ports rule at the type level: {findings}"


def test_a_ports_enum_carries_nothing_but_its_members() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "import tesser.application as ts\n"
                "class Outcome(enum.Enum):\n"
                "    FOUND = 'found'\n"
                "    NEXT = enum.auto()\n"
                "    def normalise(self, raw: str) -> str:\n"
                "        return raw.strip().lower()\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Outcome carries more than its members; a ports enum "
        "is a closed set of names and nothing else, because a method or a decorator here "
        "is logic every adapter imports" in f
        for f in findings
    ), f"an enum smuggled logic into the ports leaf: {findings}"
    assert not any("FOUND" in f or "NEXT" in f for f in findings)


def test_a_port_dto_constructor_only_assigns_its_parameters() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class Validating(ts.Response):\n"
                "    def __init__(self, id: str, name: str) -> None:\n"
                "        if not id:\n"
                "            raise ValueError('empty id')\n"
                "        self.id = id\n"
                "        self.name = name.strip()\n"
                "class Plain(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Empty(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Validating.__init__ carries logic; a port DTO "
        "constructor only assigns its parameters, because a ports module holds no "
        "logic to import" in f
        for f in findings
    ), f"domain validation lived in the ports leaf: {findings}"
    assert not any("Plain" in f or "Empty" in f for f in findings)


def test_a_port_declares_only_the_calls_an_implementer_provides() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def _raw(self, sql: str, limit: int, flag: bool) -> tuple[str, ...]: ...\n"
                "    def __enter__(self) -> str: ...\n"
                "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Sink._raw is not a call an implementer provides; "
        "a port declares only its public calls and __call__, because a private name is "
        "not private to anyone implementing or holding the port" in f
        for f in findings
    ), f"an underscore prefix bought a rule-free port method: {findings}"
    assert any("Sink.__enter__ is not a call an implementer provides" in f for f in findings)
    assert not any("Sink.save" in f for f in findings)


def test_a_ports_module_runs_nothing_at_import() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "import tesser.application as ts\n"
                "@enum.unique\n"
                "class Decorated(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Defaulted(ts.Response):\n"
                "    def __init__(self, id: str = str(enum.Enum)) -> None:\n"
                "        self.id = id\n"
                "class Generic[T](ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Computed(ts.Response, str(enum.Enum)):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id: str = id\n"
                "class Plain(ts.Response):\n"
                "    def __init__(self, id: str = 'none') -> None:\n"
                "        self.id = id\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Decorated is decorated; a ports module holds no "
        "decorator, because a decorator is a call that runs at import in the one "
        "application module adapters may import" in f
        for f in findings
    ), f"a decorator ran arbitrary code at import of the ports leaf: {findings}"
    assert any(
        "app.application.ports.sink.Defaulted.__init__ carries a computed default; a ports "
        "module holds no expression that runs at import, because every adapter imports it" in f
        for f in findings
    ), f"a default parameter expression ran at import: {findings}"
    assert any(
        "app.application.ports.sink.Computed computes a base; a ports module holds no "
        "expression that runs at import, and a base built by a call is logic every "
        "adapter imports" in f
        for f in findings
    ), f"a computed base ran at import: {findings}"
    assert any(
        "app.application.ports.sink.Generic is generic; a ports module names concrete "
        "shapes, because a type parameter is a slot the shape rules cannot read and a "
        "bound is an expression" in f
        for f in findings
    ), f"a generic port DTO went ungoverned: {findings}"
    assert not any("Plain" in f for f in findings)
    assert not any("Computed.__init__ carries logic" in f for f in findings), (
        f"an annotated self-assignment was rejected: {findings}"
    )


def test_an_async_port_method_runs_nothing_at_import() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    async def audit(self, request: SaveRequest = SaveRequest(id=open('x').read())) "
                "-> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Sink.audit carries a computed default; a ports module "
        "holds no expression that runs at import, because every adapter imports it" in f
        for f in findings
    ), f"an async def default expression ran at import: {findings}"


def test_a_port_dto_binds_only_its_own_parameters() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class Capability(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "        self.reach = __import__\n"
                "class Plain(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self._id = id\n"
                "        self.also = id\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Capability.__init__ carries logic; a port DTO "
        "constructor only assigns its parameters" in f
        for f in findings
    ), f"a DTO bound a live capability an adapter could call: {findings}"
    assert not any("Plain" in f for f in findings)


def test_a_ports_class_carries_no_keyword() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import tesser.application as ts\n"
                "class Meta(ts.Response, metaclass=type):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.Meta carries a class keyword; a ports module holds no "
        "expression that runs at import, and a metaclass is logic every adapter imports" in f
        for f in findings
    ), f"a metaclass ran logic at import of the ports leaf: {findings}"


def test_an_enum_member_may_be_negative_or_annotated() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "import tesser.application as ts\n"
                "class Outcome(enum.Enum):\n"
                "    UNKNOWN = -1\n"
                "    ALLOWED: int = 1\n"
                "    NEXT = enum.auto()\n"
                "    __doc__ = 'the verdict'\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        )
    )
    assert not any("UNKNOWN" in f or "ALLOWED" in f or "NEXT" in f for f in findings), (
        f"a legitimate enum member was rejected: {findings}"
    )
    assert any(
        "app.application.ports.sink.Outcome carries more than its members" in f
        for f in findings
    ), f"a dunder assignment laundered prose past the comments norm: {findings}"


def test_a_ports_module_computes_no_annotation() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from typing import Annotated, Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> Annotated[None, open('x').read()]:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def save[T](self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.SaveRequest.__init__ computes an annotation; a ports "
        "module holds no expression that runs at import, and an annotation is evaluated "
        "like any other" in f
        for f in findings
    ), f"an annotation ran code at import of the ports leaf: {findings}"
    assert any(
        "app.application.ports.sink.Sink.save is generic" in f for f in findings
    ), f"a generic port method went ungoverned: {findings}"


def test_every_spelling_of_a_dynamic_import_is_a_finding() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
                False,
            ),
            (
                "app/adapters/gateways/rebound.py",
                "app.adapters.gateways.rebound",
                "import importlib\n"
                "_load = importlib.import_module\n"
                "import tesser.adapters as ts\n"
                "import app.application.ports.sink as sink\n"
                "class ReachRebound(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self.svc = _load('app.application.service')\n",
                False,
            ),
            (
                "app/adapters/gateways/indirect.py",
                "app.adapters.gateways.indirect",
                "import importlib\n"
                "import tesser.adapters as ts\n"
                "import app.application.ports.sink as sink\n"
                "class ReachIndirect(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self.svc = getattr(importlib, 'import_module')"
                "('app.application.service')\n",
                False,
            ),
            (
                "app/adapters/gateways/builtin.py",
                "app.adapters.gateways.builtin",
                "import builtins\n"
                "import tesser.adapters as ts\n"
                "import app.application.ports.sink as sink\n"
                "class ReachBuiltin(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self.svc = builtins.__import__('app.application.service')\n",
                False,
            ),
            (
                "app/adapters/gateways/registry.py",
                "app.adapters.gateways.registry",
                "import sys\n"
                "import tesser.adapters as ts\n"
                "import app.application.ports.sink as sink\n"
                "class ReachRegistry(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self.svc = sys.modules['app.application.service']\n",
                False,
            ),
        )
    )
    for name in ("rebound", "indirect", "builtin", "registry"):
        assert any(f"app.adapters.gateways.{name} imports dynamically" in f for f in findings), (
            f"the {name} spelling reached application with no import edge: {findings}"
        )


def test_a_ports_module_holds_only_shapes_the_rules_can_read() -> None:
    findings = _findings(
        (
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "",
                True,
            ),
            (
                "app/application/ports/sink.py",
                "app.application.ports.sink",
                "from typing import Annotated, Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "        del id\n"
                "class Header(ts.Response, tuple[Annotated[int, 1 if True else 2], ...]):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
        )
    )
    assert any(
        "app.application.ports.sink.SaveRequest.__init__ holds a Delete; a ports module "
        "holds only the shapes its rules can read, so anything else is a finding by "
        "default rather than a gap nobody enumerated" in f
        for f in findings
    ), f"a statement kind nobody enumerated passed silently: {findings}"
    assert any(
        "app.application.ports.sink.Header holds a Subscript" in f for f in findings
    ), f"an expression in a class base ran at import: {findings}"
