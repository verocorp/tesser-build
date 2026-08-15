from __future__ import annotations

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


def test_a_conforming_spec_is_clean() -> None:
    assert tuple(
               f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
               for v in checks.Codebase(_spec()).violations()
           ) == ()


def test_placement_totality_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "plain/domain/thing.py",
                "plain.domain.thing",
                "import tesser.domain as ts\n"
                "import tesser.context as tc\n"
                "class Loose:\n"
                "    pass\n"
                "class Ask(tc.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "def stray() -> None:\n"
                "    return None\n"
                "LIMIT = 3\n"
                "print('hi')\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "plain.domain.thing.Loose" in f
        and "every context class declares its block" in f
        for f in findings
    )
    assert any(
        "plain.domain.thing.Ask" in f and "a kind lives only in its role module" in f
        for f in findings
    )
    assert any(
        "plain.domain.thing.stray" in f
        and "a module function declares itself with @ts.function" in f
        for f in findings
    )
    assert any("a module constant is Final" in f for f in findings)
    assert any(
        "a context module holds only imports, classes, declared functions, and "
        "Final constants" in f
        for f in findings
    )
    assert any(
        "imports tesser.context" in f
        and "a domain module's tesser imports are tesser.domain, "
        "tesser.errors, and tesser.serialization" in f
        for f in findings
    )


def test_declared_function_and_final_constant_pass() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("app/domain2.py", "app.domain2", "", False),
            (
                "plain/domain/thing.py",
                "plain.domain.thing",
                "from typing import Final\n"
                "import tesser.domain as ts\n"
                "LIMIT: Final[int] = 3\n"
                "@ts.function\n"
                "def declared() -> None:\n"
                "    return None\n",
                False,
            ),
        ))).violations()
               )
    assert not any("plain.domain.thing" in f for f in findings)


def test_homeless_modules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("loose.py", "loose", "def anything() -> None:\n    return None\n", False),
            (
                "stray/util.py",
                "stray.util",
                "def anything() -> None:\n    return None\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "loose belongs to no governed package; every module belongs to a context, "
        "srv, bootstrap, tests, or the protocol package" in f
        for f in findings
    )
    assert any(
        "stray.util belongs to no governed package" in f for f in findings
    )


def test_non_context_module_and_nonempty_init_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/util.py",
                "app.util",
                "def anything() -> None:\n    return None\n",
                False,
            ),
            ("app/__init__.py", "app", "X = 1\n", True),
        ))).violations()
               )
    assert any(
        "app.util" in f
        and "a context holds only domain, application, client, adapters, wiring, and tests modules" in f
        for f in findings
    )
    assert any("app" in f and "a context __init__ is empty" in f for f in findings)


def test_a_role_must_be_a_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "flat/domain.py",
                "flat.domain",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
            (
                "flat/client/client.py",
                "flat.client.client",
                "import tesser.context as ts\n"
                "class Client(ts.Client):\n"
                "    ...\n",
                False,
            ),
            ("flat/client/__init__.py", "flat.client", "", True),
        ))).violations()
               )
    assert any(
        "flat.domain is a role module; a role is a package, never a module" in f
        for f in findings
    )
    assert not any("flat.client" in f for f in findings)


def test_a_role_may_be_a_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "deep/domain/__init__.py",
                "deep.domain",
                "from deep.domain.money import Money\n",
                True,
            ),
            (
                "deep/domain/money.py",
                "deep.domain.money",
                "import tesser.domain as ts\n"
                "import deep.domain.currency as currency\n"
                "class Money(ts.ValueObject):\n"
                "    def __init__(self, amount: str, unit: currency.Currency) -> None:\n"
                "        object.__setattr__(self, '_amount', amount)\n"
                "        object.__setattr__(self, '_unit', unit)\n",
                False,
            ),
            (
                "deep/domain/currency.py",
                "deep.domain.currency",
                "import tesser.domain as ts\n"
                "class Currency(ts.ValueObject):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        object.__setattr__(self, '_code', code)\n",
                False,
            ),
            (
                "deep/domain/svc.py",
                "deep.domain.svc",
                "import tesser.application as ts\n"
                "class SneakyService(ts.ApplicationService):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "deep.domain.money" in f and "not a context module" in f for f in findings
    )
    assert not any(
        "deep.domain.money" in f and "the same-context matrix" in f for f in findings
    )
    assert any(
        "deep.domain.svc.SneakyService" in f
        and "a kind lives only in its role module" in f
        for f in findings
    )
    assert any(
        "deep.domain.svc" in f
        and "imports tesser.application" in f
        and "a domain module's tesser imports are tesser.domain, "
        "tesser.errors, and tesser.serialization" in f
        for f in findings
    )


def test_wiring_is_a_role() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "two/client/client.py",
                "two.client.client",
                "import tesser.context as ts\n"
                "class PingRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\n"
                "import app.application.service as application\n"
                "import app.client.client as client\n"
                "import two.client.client as two_client\n"
                "import two.domain.thing\n"
                "class AskWiring(ts.Wiring):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "app.wiring.wire" in f and "not a context module" in f for f in findings
    )
    assert not any(
        "app.wiring.wire" in f and "imports app.application.service" in f
        for f in findings
    )
    assert not any(
        "app.wiring.wire" in f and "imports two.client.client" in f for f in findings
    )
    assert not any(
        "app.wiring.wire.AskWiring" in f
        and "a kind lives only in its role module" in f
        for f in findings
    )
    assert any(
        "app.wiring.wire" in f
        and "imports two.domain.thing" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )


def test_tests_package_totality_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("tests/__init__.py", "tests", "X = 1\n", True),
            (
                "tests/util.py",
                "tests.util",
                "def anything() -> None:\n    return None\n",
                False,
            ),
            (
                "tests/test_ok.py",
                "tests.test_ok",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "tests __init__ declares code; "
        "a tests package holds only test modules and conftest" in f
        for f in findings
    )
    assert any(
        "tests.util is neither a test module nor conftest; "
        "a tests package holds only test modules and conftest" in f
        for f in findings
    )
    assert not any(
        "tests.test_ok" in f and "a tests package holds" in f for f in findings
    )


def test_a_context_main_is_a_stray_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/__main__.py",
                "app.__main__",
                "import app.application.service as service\nimport app.wiring.wire as wire\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.__main__ is not a context module; a context holds only domain, "
        "application, client, adapters, wiring, and tests modules" in f
        for f in findings
    )
    assert not any("__main__ composes from" in f for f in findings)


def test_protocol_module_totality_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "protocol/box.py",
                "protocol.box",
                "import tesser.srv as ts\n"
                "import json\n"
                "import app.client.client\n"
                "import srv.host\n"
                "from typing import Final, Protocol\n"
                "class BoxRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        super().__init__(text=text)\n"
                "    text: str\n"
                "class BoxResponse(ts.Response):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        super().__init__(text=text)\n"
                "    text: str\n"
                "class BoxLabel(ts.Record):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        super().__init__(text=text)\n"
                "    text: str\n"
                "class Endpoint(ts.Port, Protocol):\n"
                "    def __call__(self, request: BoxRequest) -> BoxResponse: ...\n"
                "class Loose:\n"
                "    pass\n"
                "class Server(ts.Host):\n"
                "    pass\n"
                "@ts.function\n"
                "def fine() -> None:\n"
                "    return None\n"
                "@ts.function\n"
                "def lazy() -> None:\n"
                "    import tesser.domain\n"
                "def stray() -> None:\n"
                "    return None\n"
                "LIMIT: Final[int] = 3\n"
                "ANNBARE: int = 3\n"
                "BARE = 3\n"
                "print('hi')\n",
                False,
            ),
            ("srv/host.py", "srv.host", "import tesser.srv as ts\n", False),
        ))).violations()
               )
    assert not any("protocol.box.BoxRequest" in f for f in findings)
    assert not any("protocol.box.BoxResponse" in f for f in findings)
    assert not any("protocol.box.BoxLabel" in f for f in findings)
    assert not any("protocol.box.Endpoint" in f for f in findings)
    assert not any("protocol.box.fine" in f for f in findings)
    assert not any("protocol.box belongs to no governed package" in f for f in findings)
    assert any(
        "protocol.box imports app.client.client; a protocol module is context-generic and imports no context" in f
        for f in findings
    )
    assert any(
        "protocol.box imports srv.host; a protocol module never imports srv or bootstrap" in f
        for f in findings
    )
    assert any(
        "protocol.box.Loose" in f
        and "declares no ts.* base; a protocol class declares its block" in f
        for f in findings
    )
    assert any(
        "protocol.box.Server" in f
        and "is a host; only protocol ports, protocol records, "
        "protocol rejections, protocol requests, and protocol responses live in a protocol module" in f
        for f in findings
    )
    assert any(
        "protocol.box.stray" in f
        and "a protocol function declares itself with @ts.function" in f
        for f in findings
    )
    assert (
        len(
            [
                f
                for f in findings
                if "protocol.box" in f
                and "declares a module constant without Final; a protocol constant is Final" in f
            ]
        )
        == 2
    )
    assert any(
        "protocol.box" in f
        and "imports tesser.domain inside a function; a tesser import is module-level" in f
        for f in findings
    )
    assert any(
        "protocol.box" in f
        and "has a loose module-level statement; a protocol module holds only imports, "
        "declared classes and functions, and Final constants" in f
        for f in findings
    )


def test_protocol_module_tesser_import_is_exactly_once_as_ts() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "protocol/loud.py",
                "protocol.loud",
                "import tesser.context as ts\n",
                False,
            ),
            ("protocol/quiet.py", "protocol.quiet", "", False),
            (
                "protocol/dup.py",
                "protocol.dup",
                "import tesser.srv as ts\nimport tesser.srv as ts\n",
                False,
            ),
            (
                "protocol/form.py",
                "protocol.form",
                "from tesser.srv import Request\n",
                False,
            ),
            (
                "protocol/alias.py",
                "protocol.alias",
                "import tesser.srv as tz\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "protocol.loud imports tesser.context; a protocol module imports only tesser.srv" in f
        for f in findings
    )
    assert any(
        "protocol.quiet never imports tesser.srv; a protocol module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "protocol.dup imports tesser.srv again; a protocol module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "protocol.form imports names from tesser.srv; "
        "a protocol module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "protocol.alias imports tesser.srv without the ts alias; "
        "a protocol module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )


def test_only_the_top_level_protocol_package_holds_protocol_modules() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/__init__.py", "protocol", "", True),
            ("protocol/box.py", "protocol.box", "import tesser.srv as ts\n", False),
            ("boxwire.py", "boxwire", "import tesser.srv as ts\n", False),
            ("wire.py", "wire", "import tesser.srv as ts\n", False),
        ))).violations()
               )
    assert not any("protocol/box.py" in f for f in findings)
    assert not any("protocol/__init__.py" in f for f in findings)
    assert any("boxwire belongs to no governed package" in f for f in findings)
    assert any("wire belongs to no governed package" in f for f in findings)


def test_a_protocol_init_is_empty() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/__init__.py", "protocol", "LIMIT = 3\n", True),
            ("protocol/box.py", "protocol.box", "import tesser.srv as ts\n", False),
        ))).violations()
               )
    assert any(
        "protocol __init__ declares code; a protocol __init__ is empty" in f
        for f in findings
    )
