from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest
import tesser.testing as ts

import tessercheck.domain.checks as checks


@ts.helper
def _spec(
    sources: tuple[tuple[str, str, str | None, bool], ...] = (),
    declared: str = "app",
    exports: tuple[str, ...] = (),
    imports: tuple[str, ...] = (),
    stdlib: tuple[str, ...] = (),
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
        sources=base + sources,
        declared=declared,
        nested=(),
        symlinked=(),
        exports=exports,
        imports=imports,
        stdlib=stdlib,
    )


def test_locate_is_the_single_routing_decision() -> None:
    contexts = frozenset({"app", "two"})
    table = (
        ("solo", False, "root"),
        ("test_solo", False, "test"),
        ("eval_solo", False, "eval"),
        ("conftest", False, "conftest-root"),
        ("conftest", True, "conftest-root"),
        ("weird.util", False, "root"),
        ("weird.test_x", False, "test"),
        ("weird.eval_x", False, "eval"),
        ("weird.conftest", False, "conftest"),
        ("weird.__main__", False, "root"),
        ("weird.deep.nested", False, "root"),
        ("tests", True, "root-tests"),
        ("tests", False, "root-tests"),
        ("tests.util", False, "root-tests"),
        ("tests.sub.test_deep", False, "test"),
        ("tests.test_utils", True, "test"),
        ("tests.__main__", False, "root-tests"),
        ("tests.eval_x", False, "eval"),
        ("tests.conftest", False, "conftest"),
        ("srv", True, "shell-init"),
        ("srv", False, "shell-srv"),
        ("srv.http", False, "shell-srv"),
        ("srv.__main__", False, "shell-srv"),
        ("srv.conftest", False, "conftest"),
        ("srv.deep.handler", False, "shell-srv"),
        ("bootstrap", True, "shell-init"),
        ("bootstrap", False, "shell-bootstrap"),
        ("bootstrap.wire", False, "shell-bootstrap"),
        ("bootstrap.__main__", False, "shell-bootstrap"),
        ("protocol", True, "protocol-init"),
        ("protocol", False, "protocol"),
        ("protocol.http", False, "protocol"),
        ("protocol.__main__", False, "protocol"),
        ("protocol.conftest", False, "conftest"),
        ("app", True, "context-init"),
        ("app", False, "context-init"),
        ("app.__main__", False, "context-stray"),
        ("app.domain", True, "role-init"),
        ("app.domain", False, "role-file"),
        ("app.domain.thing", False, "role"),
        ("app.domain.__main__", False, "role"),
        ("app.domain.sub.deep", False, "role"),
        ("app.domain.test_thing", False, "test"),
        ("app.domain.eval_bad", False, "eval"),
        ("app.domain.eval_pkg", True, "eval"),
        ("app.domain.conftest", False, "conftest"),
        ("app.application", True, "role-init"),
        ("app.application.service", False, "role"),
        ("app.application.ports", True, "ports-init"),
        ("app.application.ports", False, "ports-file"),
        ("app.application.ports.repo", False, "ports"),
        ("app.application.ports.sub.deep", False, "ports"),
        ("app.application.ports.__main__", False, "ports"),
        ("app.application.ports.test_repo", False, "ports-stray"),
        ("app.application.ports.conftest", False, "ports-stray"),
        ("app.application.ports.eval_repo", False, "ports-stray"),
        ("app.adapters.gateways.__main__", False, "role"),
        ("app.adapters.conftest", False, "conftest"),
        ("app.adapters.conftest", True, "conftest"),
        ("app.tests", True, "context-tests-init"),
        ("app.tests", False, "context-tests-stray"),
        ("app.tests.support", False, "context-tests-stray"),
        ("app.tests.test_thing", False, "test"),
        ("app.tests.__main__", False, "context-tests-stray"),
        ("app.test_direct", False, "test"),
        ("app.stray", False, "context-stray"),
        ("app.stray_pkg.mod", False, "context-stray"),
        ("app.conftest", False, "conftest"),
        ("kernel", True, "kernel-init"),
        ("kernel", False, "kernel-file"),
        ("kernel.money", False, "kernel"),
        ("kernel.sub", True, "kernel-init"),
        ("kernel.sub.deep", False, "kernel"),
        ("kernel.__main__", False, "kernel"),
        ("kernel.test_money", False, "test"),
        ("kernel.conftest", False, "conftest"),
    )
    for name, is_package, expected in table:
        got = checks.Codebase._locate(name, is_package, contexts)
        assert got == expected, (
            f"_locate({name!r}, is_package={is_package}) = {got!r}, expected {expected!r}"
        )
    exported = (
        ("shells", True, "kernel-init"),
        ("shells", False, "kernel-file"),
        ("shells.valueobject", False, "kernel"),
        ("shells.domain.base", False, "kernel"),
        ("shells.test_base", False, "test"),
    )
    for name, is_package, expected in exported:
        got = checks.Codebase._locate(name, is_package, contexts, "shells")
        assert got == expected, (
            f"_locate({name!r}, is_package={is_package}, export='shells') = {got!r}, "
            f"expected {expected!r}"
        )
    assert checks.Codebase._locate("shells.thing", False, contexts) == "root", (
        "an undeclared export directory must classify as it always did"
    )
    locate_tree = ast.parse(
        textwrap.dedent(inspect.getsource(checks.Codebase._locate))
    )
    locate = next(
        node for node in locate_tree.body if isinstance(node, ast.FunctionDef)
    )
    returned = frozenset(
        value.value
        for stmt in ast.walk(locate)
        if isinstance(stmt, ast.Return) and stmt.value is not None
        for value in ast.walk(stmt.value)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    )
    exercised = frozenset(expected for _, _, expected in table)
    assert returned == exercised, (
        f"the classification table and _locate's return set drifted apart: "
        f"unexercised tokens {sorted(returned - exercised)}, "
        f"stale table rows {sorted(exercised - returned)}"
    )


def test_every_location_token_has_a_dispatch_arm() -> None:
    locate_tree = ast.parse(
        textwrap.dedent(inspect.getsource(checks.Codebase._locate))
    )
    locate = next(
        node for node in locate_tree.body if isinstance(node, ast.FunctionDef)
    )
    tokens = frozenset(
        value.value
        for stmt in ast.walk(locate)
        if isinstance(stmt, ast.Return) and stmt.value is not None
        for value in ast.walk(stmt.value)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    )
    dispatch_tree = ast.parse(
        textwrap.dedent(inspect.getsource(checks.Codebase._module_violations))
    )
    dispatch = next(
        node for node in dispatch_tree.body if isinstance(node, ast.FunctionDef)
    )
    handled = frozenset(
        node.comparators[0].value
        for node in ast.walk(dispatch)
        if isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == "place"
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
    )
    assert tokens, "no tokens extracted from _locate"
    unhandled = tokens - handled - {"context-stray"}
    assert unhandled == frozenset(), (
        f"_locate can return tokens with no dispatch arm: {sorted(unhandled)} "
        "(context-stray is the dispatch's final return)"
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
        "a kernel, srv, bootstrap, tests, or the protocol package" in f
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


def test_import_matrix_is_flagged() -> None:
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
                "two/adapters/gateways.py",
                "two.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import app.client.client as app_client\n"
                "class Bridge(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
            (
                "two/domain/thing.py",
                "two.domain.thing",
                "import tesser.domain as ts\n"
                "import two.client.client\n"
                "class TwoSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "two/application/service.py",
                "two.application.service",
                "import tesser.application as ts\n"
                "import app.domain.thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "two.domain.thing" in f
        and "the same-context matrix is a role to itself, application to domain and client, adapters to application/ports, wiring to application, adapters, and client" in f
        for f in findings
    )
    assert any(
        "two.application.service" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )
    assert not any("two.adapters.gateways" in f and "imports app.client.client" in f for f in findings)


def test_srv_and_bootstrap_import_rows() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
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
                "two/adapters/gateways.py",
                "two.adapters.gateways",
                "import tesser.adapters as ts\n"
                "class Bridge(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
            (
                "srv/http.py",
                "srv.http",
                "import app.application.service\n"
                "import app.adapters.gateways as app_adapters\n"
                "import two.adapters.gateways\n"
                "import bootstrap.wire\n",
                False,
            ),
            (
                "bootstrap/wire.py",
                "bootstrap.wire",
                "import app.domain.thing\n"
                "import app.wiring.wire as wiring\n"
                "import app.client.client as app_client\n"
                "import srv.http\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.http" in f and "imports app.application.service" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert any(
        "srv.http" in f and "imports two.adapters.gateways" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.http" in f and "imports app.adapters.gateways" in f for f in findings)
    assert not any("srv.http" in f and "imports bootstrap.wire" in f for f in findings)
    assert any(
        "bootstrap.wire" in f and "imports app.domain.thing" in f
        and "bootstrap builds from wiring, clients, and adapters, never domain or application" in f
        for f in findings
    )
    assert not any("bootstrap.wire" in f and "imports app.wiring.wire" in f for f in findings)
    assert not any("bootstrap.wire" in f and "imports app.client.client" in f for f in findings)
    assert any(
        "bootstrap.wire" in f and "imports srv.http" in f
        and "the composition root never imports a host" in f
        for f in findings
    )


def test_only_a_handler_imports_its_own_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import app.client.client as app_client\n"
                "class HttpHandler(ts.Handler):\n"
                "    def ask(self, body: str) -> str:\n"
                "        return app_client.AskRequest(text=body).text\n",
                False,
            ),
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
                "two/adapters/gateways.py",
                "two.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import two.client.client\n"
                "class SneakyGateway(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.adapters.gateways" in f and "imports app.client.client" in f for f in findings)
    assert any(
        "two.adapters.gateways" in f and "imports two.client.client" in f
        and "only a handler imports its own context's client" in f
        for f in findings
    )


def test_only_a_gateway_reaches_a_foreign_client() -> None:
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
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import two.client.client\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.adapters.gateways" in f and "imports two.client.client" in f
        and "a context reaches another context only through its client, and only from gateways and wiring" in f
        for f in findings
    )


def test_role_module_tesser_import_is_exactly_once_as_ts() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "lone/domain/thing.py",
                "lone.domain.thing",
                "class Bare:\n"
                "    pass\n",
                False,
            ),
            (
                "noalias/domain/thing.py",
                "noalias.domain.thing",
                "import tesser.domain as td\n"
                "class ThingSpec(td.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "fromform/domain/thing.py",
                "fromform.domain.thing",
                "from tesser.domain import Spec\n"
                "class OtherSpec(Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "dup/domain/thing.py",
                "dup.domain.thing",
                "import tesser.domain as ts\n"
                "import tesser.domain as ts\n"
                "class DupSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "lone.domain.thing never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "noalias.domain.thing imports tesser.domain without the ts alias; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "fromform.domain.thing imports names from tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "dup.domain.thing imports tesser.domain again; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )


def test_reexport_only_role_init_needs_no_tesser_import() -> None:
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
                "class Money(ts.ValueObject):\n"
                "    def __init__(self, amount: str) -> None:\n"
                "        object.__setattr__(self, '_amount', amount)\n",
                False,
            ),
        ))).violations()
               )
    assert not any("deep.domain" in f and "exactly once, as ts" in f for f in findings)


def test_role_init_only_reexports_its_own_role() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "pkg/domain/__init__.py",
                "pkg.domain",
                "import tesser.domain as ts\n"
                "from pkg.domain.vo import Tag\n"
                "LIMIT = 3\n",
                True,
            ),
            (
                "pkg/domain/vo.py",
                "pkg.domain.vo",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "pkg.domain imports tesser.domain; a role __init__ only re-exports from its own role" in f
        for f in findings
    )
    assert any(
        "pkg.domain __init__ declares code; "
        "a role __init__ only re-exports from its own role" in f
        for f in findings
    )
    assert not any("imports pkg.domain.vo" in f for f in findings)
    assert any(
        "pkg.domain imports names from pkg.domain.vo; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )


def test_a_role_init_may_import_a_module_but_never_a_class() -> None:
    vo = (
        "mod/domain/vo.py",
        "mod.domain.vo",
        "import tesser.domain as ts\n"
        "class Tag(ts.ValueObject):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        object.__setattr__(self, '_text', text)\n",
        False,
    )
    client = (
        "mod/client/client.py",
        "mod.client.client",
        "import tesser.context as ts\n"
        "class AskRequest(ts.Request):\n"
        "    def __init__(self, text: str) -> None:\n"
        "        self.text = text\n",
        False,
    )
    client_init = ("mod/client/__init__.py", "mod.client", "", True)
    module_form = (
        "mod/domain/__init__.py",
        "mod.domain",
        "import mod.domain.vo as vo\n",
        True,
    )
    class_form = (
        "mod/domain/__init__.py",
        "mod.domain",
        "from mod.domain.vo import Tag\n",
        True,
    )
    assert not any(
        "mod.domain:" in f for f in tuple(
                                        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                                        for v in checks.Codebase(_spec(sources=(vo, module_form, client, client_init))).violations()
                                    )
    )

    assert any(
        "mod.domain imports names from mod.domain.vo; "
        "a context module is imported as an aliased module, never its members" in f
        for f in tuple(
                     f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                     for v in checks.Codebase(_spec(sources=(vo, class_form, client, client_init))).violations()
                 )
    )


def test_srv_and_bootstrap_statement_totality() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/box.py",
                "srv.box",
                "import tesser.srv as ts\n"
                "import tesser.domain as td\n"
                "@ts.function\n"
                "def fine() -> None:\n"
                "    return None\n"
                "def stray() -> None:\n"
                "    return None\n"
                "class Box:\n"
                "    pass\n"
                "class Server(ts.Host):\n"
                "    pass\n"
                "LIMIT = 3\n"
                "print('hi')\n",
                False,
            ),
            (
                "bootstrap/wire.py",
                "bootstrap.wire",
                "def build() -> None:\n"
                "    return None\n"
                "class App:\n"
                "    pass\n"
                "LIMIT = 3\n"
                "print('hi')\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.box imports tesser.domain; a srv module's tesser imports "
        "are tesser.srv, tesser.errors, and tesser.lifecycle" in f
        for f in findings
    )
    assert any(
        "srv.box.stray" in f
        and "a srv function declares itself with @ts.function" in f
        for f in findings
    )
    assert not any("srv.box.fine" in f for f in findings)
    assert any(
        "srv.box.Box" in f and "declares no ts.* base; a srv class declares its block" in f
        for f in findings
    )
    assert not any("srv.box.Server" in f for f in findings)
    assert any(
        "srv.box" in f and "declares a module constant without Final; a srv constant is Final" in f
        for f in findings
    )
    assert any(
        "srv.box" in f and "has a loose module-level statement; a srv module holds only imports, "
        "declared classes and functions, and Final constants" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire never imports tesser.context; "
        "a bootstrap module imports tesser.context exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire.build" in f
        and "a bootstrap function declares itself with @ts.function" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire.App" in f
        and "is a class; a bootstrap module holds only imports, declared functions, "
        "and Final constants" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire" in f
        and "declares a module constant without Final; a bootstrap constant is Final" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire" in f
        and "has a loose module-level statement; a bootstrap module holds only imports, "
        "declared functions, and Final constants" in f
        for f in findings
    )


def test_pure_core_stdlib_allowlist() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "io1/domain/thing.py",
                "io1.domain.thing",
                "import os\n"
                "import datetime\n"
                "import tesser.domain as ts\n"
                "class StampSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "io1/client/client.py",
                "io1.client.client",
                "from __future__ import annotations\n"
                "import datetime\n"
                "import tesser.context as ts\n"
                "class StampRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "io1/adapters/gateways.py",
                "io1.adapters.gateways",
                "from pathlib import Path\n"
                "import tesser.adapters as ts\n"
                "class DiskRepository(ts.Repository):\n"
                "    def load(self, key: str) -> str: ...\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "io1.domain.thing imports os; domain, client, and application "
        "import only their context, their kernels, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert not any("io1.domain.thing imports datetime" in f for f in findings)
    assert any(
        "io1.client.client imports datetime; domain, client, and application "
        "import only their context, their kernels, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert not any("imports __future__" in f for f in findings)
    assert not any("io1.adapters.gateways" in f and "the pure stdlib" in f for f in findings)


def test_context_module_import_form() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "form/client/client.py",
                "form.client.client",
                "import tesser.context as ts\n"
                "class PingRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "form/application/service.py",
                "form.application.service",
                "import tesser.application as ts\n"
                "from form.client.client import PingRequest\n",
                False,
            ),
            (
                "form/wiring/wire.py",
                "form.wiring.wire",
                "import tesser.context as ts\n"
                "import form.application.service\n"
                "class PingWiring(ts.Wiring):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "form.application.service imports names from form.client.client; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )
    assert any(
        "form.wiring.wire imports form.application.service without an alias; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )


def test_relative_imports_resolve_against_the_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "rel/domain/__init__.py",
                "rel.domain",
                "from .money import Money\n",
                True,
            ),
            (
                "rel/domain/money.py",
                "rel.domain.money",
                "import tesser.domain as ts\n"
                "class Money(ts.ValueObject):\n"
                "    def __init__(self, amount: str) -> None:\n"
                "        object.__setattr__(self, '_amount', amount)\n",
                False,
            ),
            (
                "rel/client/client.py",
                "rel.client.client",
                "import tesser.context as ts\n"
                "class RelRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "rel/wiring/wire.py",
                "rel.wiring.wire",
                "import tesser.context as ts\n"
                "from ..client.client import RelRequest\n"
                "class RelWiring(ts.Wiring):\n"
                "    pass\n",
                False,
            ),
            (
                "rel/adapters/repo.py",
                "rel.adapters.repo",
                "import tesser.adapters as ts\n"
                "from ..domain.money import Money\n"
                "class LoadingRepo(ts.Repository):\n"
                "    def load(self, key: str) -> Money: ...\n",
                False,
            ),
            (
                "rel/adapters/beyond.py",
                "rel.adapters.beyond",
                "import tesser.adapters as ts\n"
                "from ...domain.money import Money\n"
                "class BeyondRepo(ts.Repository):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any("rel.domain" in f and "a role __init__ only re-exports from its own role" in f for f in findings)
    assert any(
        "rel.adapters.beyond imports ...domain.money beyond the package root; "
        "a relative import resolves inside the tree" in f
        for f in findings
    )
    assert any(
        "rel.wiring.wire imports names from rel.client.client; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )
    assert any(
        "rel.adapters.repo imports rel.domain.money; the same-context matrix" in f
        for f in findings
    )
    assert any(
        "LoadingRepo.load" in f and "an adapter speaks records, never domain objects" in f
        for f in findings
    )


def test_nested_imports_neither_classify_nor_satisfy_presence() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "lazy/domain/thing.py",
                "lazy.domain.thing",
                "class HiddenSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        import tesser.domain as ts\n"
                "        self.text = text\n",
                False,
            ),
            (
                "lazy2/domain/thing.py",
                "lazy2.domain.thing",
                "import tesser.domain as ts\n"
                "class LazySpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        import os\n"
                "        self.text = text\n",
                False,
            ),
            (
                "lazy3/domain/thing.py",
                "lazy3.domain.thing",
                "import tesser.domain as ts\n"
                "class GoodSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        import tesser.context as tc\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "lazy.domain.thing never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "lazy.domain.thing.HiddenSpec" in f and "declares no ts.* base" in f for f in findings
    )
    assert any(
        "lazy2.domain.thing imports os; domain, client, and application "
        "import only their context, their kernels, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert any(
        "lazy3.domain.thing imports tesser.context inside a function; "
        "a tesser import is module-level" in f
        for f in findings
    )


def test_srv_and_bootstrap_tesser_form_modes() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/dup.py",
                "srv.dup",
                "import tesser.srv as ts\n"
                "import tesser.srv as ts\n"
                "@ts.function\n"
                "def go() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "srv/alias.py",
                "srv.alias",
                "import tesser.srv as tc\n"
                "@tc.function\n"
                "def go() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "bootstrap/fromform.py",
                "bootstrap.fromform",
                "from tesser.context import function\n"
                "@function\n"
                "def go() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "bootstrap/wrongpkg.py",
                "bootstrap.wrongpkg",
                "import tesser.context as ts\n"
                "import tesser.domain as td\n",
                False,
            ),
            (
                "srv/consts.py",
                "srv.consts",
                "from typing import Final\n"
                "LIMIT: Final[int] = 3\n",
                False,
            ),
            (
                "srv/annconst.py",
                "srv.annconst",
                "LIMIT: int = 3\n",
                False,
            ),
            (
                "srv/tfinal.py",
                "srv.tfinal",
                "import tesser.srv as ts\n"
                "import typing\n"
                "LIMIT: typing.Final[int] = 3\n",
                False,
            ),
            ("srv/__init__.py", "srv", "X = 1\n", True),
            ("bootstrap/__init__.py", "bootstrap", "", True),
            (
                "konst/domain/thing.py",
                "konst.domain.thing",
                "from typing import Final\n"
                "LIMIT: Final[int] = 3\n",
                False,
            ),
        ), base=())).violations()
               )
    assert any(
        "srv.dup imports tesser.srv again; "
        "a srv module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "srv.alias imports tesser.srv without the ts alias; "
        "a srv module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "bootstrap.fromform imports names from tesser.context; "
        "a bootstrap module imports tesser.context exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "bootstrap.wrongpkg imports tesser.domain; "
        "a bootstrap module's tesser imports are tesser.context, "
        "tesser.errors, and tesser.lifecycle" in f
        for f in findings
    )
    assert any(
        "srv.consts never imports tesser.srv; "
        "a srv module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "srv.annconst declares a module constant without Final; "
        "a srv constant is Final" in f
        for f in findings
    )
    assert not any("srv.tfinal" in f for f in findings)
    assert any(
        "konst.domain.thing never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "srv __init__ declares code; a srv or bootstrap __init__ is empty" in f
        for f in findings
    )
    assert not any("bootstrap __init__ declares code" in f for f in findings)


def test_pure_core_allowlist_covers_application_and_domain_future() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "io2/domain/thing.py",
                "io2.domain.thing",
                "from __future__ import annotations\n"
                "import tesser.domain as ts\n"
                "class DSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "io2/application/service.py",
                "io2.application.service",
                "from __future__ import annotations\n"
                "import typing\n"
                "import socket\n"
                "import tesser.application as ts\n"
                "class NopService(ts.ApplicationService):\n"
                "    pass\n",
                False,
            ),
        ), base=())).violations()
               )
    assert not any("io2.domain.thing" in f and "the pure stdlib" in f for f in findings)
    assert any(
        "io2.application.service imports socket; domain, client, and application "
        "import only their context, their kernels, their tesser package, and the pure stdlib" in f
        for f in findings
    )
    assert not any("io2.application.service:1" in f for f in findings)
    assert not any("io2.application.service:2" in f for f in findings)


def test_srv_kinds_stay_out_of_contexts_and_context_kinds_out_of_srv() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import tesser.srv\n"
                "from typing import Protocol\n"
                "class Sneaky(tesser.srv.Host):\n"
                "    pass\n"
                "class WireAsk(tesser.srv.Request):\n"
                "    pass\n"
                "class WireReply(tesser.srv.Response):\n"
                "    pass\n"
                "class WireDoor(tesser.srv.Port, Protocol):\n"
                "    def __call__(self) -> None: ...\n"
                "class WireLabel(tesser.srv.Record):\n"
                "    pass\n",
                False,
            ),
            (
                "srv/box.py",
                "srv.box",
                "import tesser.srv as ts\n"
                "import tesser.domain\n"
                "class Value(tesser.domain.ValueObject):\n"
                "    pass\n"
                "class Turn(ts.Response):\n"
                "    pass\n"
                "class Label(ts.Record):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.adapters.gateways.Sneaky" in f
        and "is a host; a host lives in srv and a protocol kind in a protocol module, never a context" in f
        for f in findings
    )
    assert any(
        "app.adapters.gateways.WireAsk" in f
        and "is a protocol request record; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "app.adapters.gateways.WireReply" in f
        and "is a protocol response record; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "app.adapters.gateways.WireDoor" in f
        and "is a protocol port; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "app.adapters.gateways.WireLabel" in f
        and "is a protocol record; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "srv.box.Value" in f and "is a value object; only a host class lives in a srv module" in f
        for f in findings
    )
    assert any(
        "srv.box.Turn" in f
        and "is a protocol response record; only a host class lives in a srv module" in f
        for f in findings
    )
    assert any(
        "srv.box.Label" in f
        and "is a protocol record; only a host class lives in a srv module" in f
        for f in findings
    )


def test_form_rule_fires_in_tests_and_srv_and_skips_illegal_edges() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_forms.py",
                "app.test_forms",
                "from app.domain.thing import Thing\n"
                "def test_thing() -> None:\n"
                "    assert Thing\n",
                False,
            ),
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            (
                "srv/http.py",
                "srv.http",
                "from app.adapters.gateways import HttpHandler\n",
                False,
            ),
            (
                "skipctx/domain/thing.py",
                "skipctx.domain.thing",
                "import tesser.domain as ts\n"
                "from app.client.client import AskRequest\n"
                "class SkipSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.test_forms imports names from app.domain.thing; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )
    assert any(
        "srv.http imports names from app.adapters.gateways; "
        "a context module is imported as an aliased module, never its members" in f
        for f in findings
    )
    assert any(
        "skipctx.domain.thing imports app.client.client; a context reaches another context "
        "only through its client, and only from gateways and wiring" in f
        for f in findings
    )
    assert not any(
        "skipctx.domain.thing" in f and "a context module is imported as an aliased module" in f
        for f in findings
    )


def test_a_denied_app_edge_is_not_form_checked() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/host.py",
                "srv.host",
                "import tesser.srv as ts\n"
                "from app.domain import thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.host imports app.domain" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.host" in f and "never its members" in f for f in findings)


def test_production_never_imports_the_tests_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_ok.py",
                "tests.test_ok",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "srv/http.py",
                "srv.http",
                "import tests.test_ok\n",
                False,
            ),
            (
                "bootstrap/wire.py",
                "bootstrap.wire",
                "import protocol.http\nimport tests.test_ok\n",
                False,
            ),
            (
                "protocol/http.py",
                "protocol.http",
                "import tesser.srv as ts\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.http imports tests.test_ok; "
        "production code never imports the tests package" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire imports tests.test_ok; "
        "production code never imports the tests package" in f
        for f in findings
    )
    assert any(
        "bootstrap.wire imports protocol.http; "
        "bootstrap composes the application and never imports protocol" in f
        for f in findings
    )


def test_a_context_role_reaches_the_app_shell_only_as_handlers_to_protocol() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "protocol/http.py",
                "protocol.http",
                "import tesser.srv as ts\n",
                False,
            ),
            (
                "app/adapters/handlers.py",
                "app.adapters.handlers",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n"
                "import srv.http as host\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\n"
                "import protocol.http as http\n",
                False,
            ),
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n"
                "class PeerGateway(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
            (
                "app/adapters/handlers_support.py",
                "app.adapters.handlers_support",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n",
                False,
            ),
            ("app/adapters/repositories/__init__.py", "app.adapters.repositories", "", True),
            (
                "app/adapters/repositories/smuggle.py",
                "app.adapters.repositories.smuggle",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n"
                "class SmuggleHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            ("srv/http.py", "srv.http", "", False),
        ))).violations()
               )
    clause = "of the app shell a context imports only protocol, and only from its handlers"
    assert any(
        "app.adapters.handlers imports srv.http; "
        "of the app shell a context imports only protocol, and only from its handlers" in f
        for f in findings
    )
    assert not any("app.adapters.handlers imports protocol.http" in f for f in findings)
    assert any(f"app.wiring.wire imports protocol.http; {clause}" in f for f in findings)
    assert any(
        f"app.adapters.gateways imports protocol.http; {clause}" in f for f in findings
    ), f"a gateway imported protocol without a finding: {findings}"
    assert any(
        f"app.adapters.handlers_support imports protocol.http; {clause}" in f
        for f in findings
    ), f"a handlers-adjacent name bought the grant without the placement: {findings}"
    assert any(
        f"app.adapters.repositories.smuggle imports protocol.http; {clause}" in f
        for f in findings
    ), f"a Handler class declared outside handlers/ bought the grant: {findings}"


def test_a_classless_module_inside_handlers_may_speak_protocol() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/http.py", "protocol.http", "import tesser.srv as ts\n", False),
            ("app/adapters/handlers/__init__.py", "app.adapters.handlers", "", True),
            (
                "app/adapters/handlers/usage.py",
                "app.adapters.handlers.usage",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "app.adapters.handlers.usage imports protocol.http" in f for f in findings
    ), f"a helper module inside handlers/ was denied protocol: {findings}"


def test_a_shell_name_missing_from_the_tree_is_not_the_shell() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/test_thing.py",
                "app.domain.test_thing",
                "import protocol.thirdparty\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\nimport bootstrap\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.domain.test_thing imports protocol.thirdparty" in f for f in findings)
    assert not any("app.wiring.wire imports bootstrap" in f for f in findings)


def test_a_vendored_tesser_package_is_not_the_tree() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("tesser/testing.py", "tesser.testing", "X = 1\n", False),
            ("conftest.py", "conftest", "import tesser.testing\n", False),
        ))).violations()
               )
    assert not any(
        "conftest imports tesser.testing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )


def test_a_root_module_is_homeless() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "helpers.py",
                "helpers",
                "import app.domain.thing\nimport enum\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "helpers belongs to no governed package; every module belongs to a "
        "context, a kernel, srv, bootstrap, tests, or the protocol package" in f
        for f in findings
    )


def test_a_root_conftest_is_a_leaf() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "conftest.py",
                "conftest",
                "import os\nimport sys\nimport app.domain.thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "conftest imports app.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert not any("imports os" in f for f in findings)


def test_a_protocol_module_imports_nothing_else_from_its_tree() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("serialization.py", "serialization", "X = 1\n", False),
            (
                "protocol/http.py",
                "protocol.http",
                "import tesser.srv as ts\nimport serialization\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "protocol.http imports serialization; "
        "a protocol module imports nothing else from its tree" in f
        for f in findings
    )


def test_a_norm_module_is_from_imported_where_its_placement_allows() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "fine/domain/money.py",
                "fine.domain.money",
                "import tesser.domain as ts\n"
                "from tesser.serialization import canonical_str\n"
                "class MoneySpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = canonical_str(code)\n",
                False,
            ),
            (
                "whole/domain/money.py",
                "whole.domain.money",
                "import tesser.domain as ts\n"
                "import tesser.serialization\n"
                "class WholeSpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = code\n",
                False,
            ),
            (
                "appside/application/service.py",
                "appside.application.service",
                "import tesser.application as ts\n"
                "from tesser.serialization import canonical_str\n"
                "class SideService(ts.ApplicationService):\n"
                "    def ask(self, code: str) -> str:\n"
                "        return canonical_str(code)\n",
                False,
            ),
            (
                "only/domain/money.py",
                "only.domain.money",
                "from tesser.serialization import canonical_str\n"
                "class OnlyMoney:\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = canonical_str(code)\n",
                False,
            ),
        ))).violations()
               )
    assert not any("fine.domain.money" in f for f in findings)
    assert any(
        "whole.domain.money imports tesser.serialization whole; a norm module "
        "is from-imported by name, never whole — the ts alias belongs to the "
        "placement's own package" in f
        for f in findings
    )
    assert any(
        "appside.application.service imports tesser.serialization; "
        "an application module's tesser imports are "
        "tesser.application and tesser.errors" in f
        for f in findings
    )
    assert any(
        "only.domain.money never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )


def test_wiring_bootstrap_and_srv_may_from_import_tesser_lifecycle() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\n"
                "from tesser.lifecycle import Closeable\n"
                "class Wiring(ts.Wiring):\n"
                "    def closeables(self) -> tuple[Closeable, ...]:\n"
                "        return ()\n",
                False,
            ),
            (
                "bootstrap/wire.py",
                "bootstrap.wire",
                "import tesser.context as ts\n"
                "from tesser.lifecycle import Closeable\n",
                False,
            ),
            (
                "srv/run.py",
                "srv.run",
                "import tesser.srv as ts\n"
                "from tesser.lifecycle import Closeable\n",
                False,
            ),
            (
                "astray/wiring/wire.py",
                "astray.wiring.wire",
                "import tesser.context as ts\n"
                "import tesser.domain\n"
                "class Wiring(ts.Wiring):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.wiring.wire" in f for f in findings)
    assert not any("bootstrap.wire" in f and "tesser.lifecycle" in f for f in findings)
    assert not any("srv.run" in f and "tesser.lifecycle" in f for f in findings)
    assert any(
        "astray.wiring.wire imports tesser.domain; "
        "a wiring module's tesser imports are tesser.context, "
        "tesser.errors, and tesser.lifecycle" in f
        for f in findings
    )


def test_any_role_but_client_may_from_import_tesser_errors() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/money.py",
                "app.domain.money",
                "import tesser.domain as ts\n"
                "from tesser.errors import invalid\n"
                "class MoneySpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        if not code:\n"
                "            raise invalid(\"bad_code\", \"code is empty\")\n"
                "        self.code = code\n",
                False,
            ),
            (
                "app/application/views.py",
                "app.application.views",
                "import tesser.application as ts\n"
                "import app.client.client as client\n"
                "from tesser.errors import not_found\n"
                "class ViewService(ts.ApplicationService):\n"
                "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
                "        raise not_found(\"no_row\", request.text)\n",
                False,
            ),
            (
                "app/adapters/gateways.py",
                "app.adapters.gateways",
                "import tesser.adapters as ts\n"
                "from tesser.errors import InfraError\n"
                "class MemoryGateway(ts.Gateway):\n"
                "    def load(self, key: str) -> str:\n"
                "        raise InfraError(key)\n",
                False,
            ),
            (
                "stray/client/client.py",
                "stray.client.client",
                "import tesser.context as ts\n"
                "from tesser.errors import invalid\n"
                "class AskRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "astray/adapters/gateways.py",
                "astray.adapters.gateways",
                "import tesser.adapters as ts\n"
                "from tesser.serialization import canonical_str\n"
                "class StrayGateway(ts.Gateway):\n"
                "    def load(self, key: str) -> str:\n"
                "        return canonical_str(key)\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.domain.money" in f for f in findings)
    assert not any("app.application.views" in f for f in findings)
    assert not any("app.adapters.gateways" in f for f in findings)
    assert any(
        "stray.client.client imports tesser.errors; "
        "a role module imports only its own tesser package" in f
        for f in findings
    )
    assert any(
        "astray.adapters.gateways imports tesser.serialization; "
        "an adapters module's tesser imports are "
        "tesser.adapters and tesser.errors" in f
        for f in findings
    )


def test_an_eval_lives_only_in_a_gateway() -> None:
    body = (
        "import tesser.testing as ts\n"
        "def test_model_picks_a_tool() -> None:\n"
        "    assert True\n"
    )
    loose = (
        ("app/adapters/eval_flat.py", "app.adapters.eval_flat", body, False),
        ("app/tests/__init__.py", "app.tests", "", True),
        ("app/tests/eval_tier.py", "app.tests.eval_tier", body, False),
        ("app/domain/eval_role.py", "app.domain.eval_role", body, False),
    )
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=loose)).violations()
               )
    for outside in ("app.adapters.eval_flat", "app.tests.eval_tier", "app.domain.eval_role"):
        assert any(
            f"{outside} is an eval outside a gateway; an eval lives only in a gateway, "
            "the one place a sampled real-model call is honest" in f
            for f in findings
        ), outside

    housed = tuple(
                 f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                 for v in checks.Codebase(_spec(sources=loose
        + (
            (
                "app/adapters/gateways/__init__.py",
                "app.adapters.gateways",
                "",
                True,
            ),
            (
                "app/adapters/gateways/eval_llm.py",
                "app.adapters.gateways.eval_llm",
                body,
                False,
            ),
            (
                "app/adapters/gateways/llm/__init__.py",
                "app.adapters.gateways.llm",
                "",
                True,
            ),
            (
                "app/adapters/gateways/llm/evals/__init__.py",
                "app.adapters.gateways.llm.evals",
                "",
                True,
            ),
            (
                "app/adapters/gateways/llm/evals/eval_tools.py",
                "app.adapters.gateways.llm.evals.eval_tools",
                body,
                False,
            ),
        ))).violations()
             )
    assert not any("eval_llm is an eval outside a gateway" in f for f in housed)
    assert not any("eval_tools is an eval outside a gateway" in f for f in housed)


def test_a_handler_sibling_fakes_only_the_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/handlers/http.py",
                "app.adapters.handlers.http",
                "import tesser.adapters as ts\n"
                "import app.client.client as client\n"
                "class Handler(ts.Handler):\n"
                "    def __init__(self, c: client.Client) -> None:\n"
                "        self._c = c\n",
                False,
            ),
            ("app/adapters/handlers/__init__.py", "app.adapters.handlers", "", True),
            ("app/adapters/__init__.py", "app.adapters", "", True),
            (
                "app/adapters/handlers/test_http.py",
                "app.adapters.handlers.test_http",
                "import tesser.testing as ts\n"
                "import app.adapters.handlers.http as http\n"
                "import app.client.client as client\n"
                "import app.application.service as application\n"
                "import app.adapters.gateways as gateways\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("app/adapters/gateways/__init__.py", "app.adapters.gateways", "", True),
        ))).violations()
               )
    assert any(
        "app.adapters.handlers.test_http imports app.application.service, but a test "
        "placed in handlers reaches only adapters.handlers, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "app.adapters.handlers.test_http imports app.adapters.gateways, but a test "
        "placed in handlers reaches only adapters.handlers, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_http:2" in f for f in findings)
    assert not any("test_http:3" in f for f in findings)


def test_a_srv_test_reaches_a_context_only_through_its_handlers() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/handlers/http.py",
                "app.adapters.handlers.http",
                "import tesser.adapters as ts\n"
                "import app.client.client as client\n"
                "class Handler(ts.Handler):\n"
                "    def __init__(self, c: client.Client) -> None:\n"
                "        self._c = c\n",
                False,
            ),
            ("app/adapters/handlers/__init__.py", "app.adapters.handlers", "", True),
            ("app/adapters/__init__.py", "app.adapters", "", True),
            (
                "srv/test_router.py",
                "srv.test_router",
                "import tesser.testing as ts\n"
                "import app.adapters.handlers.http as http\n"
                "import app.application.service as application\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.test_router imports app.application.service, but a test placed in "
        "srv reaches a context only through its handlers; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_router:2" in f for f in findings)


def test_a_test_reaches_only_what_its_placement_allows() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "far/domain/test_thing.py",
                "far.domain.test_thing",
                "import tesser.testing as ts\n"
                "import far.client.client as client\n"
                "import app.client.client as foreign\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "far/domain/thing.py",
                "far.domain.thing",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
            (
                "far/client/client.py",
                "far.client.client",
                "import tesser.context as ts\n"
                "class Client(ts.Client):\n"
                "    ...\n",
                False,
            ),
            ("far/domain/__init__.py", "far.domain", "", True),
            ("far/client/__init__.py", "far.client", "", True),
        ))).violations()
               )
    assert any(
        "far.domain.test_thing imports far.client.client, but a test placed in domain "
        "reaches only domain of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "far.domain.test_thing imports app.client.client, but a test placed in domain "
        "reaches no neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )


def test_a_repository_sibling_test_reaches_its_kind_and_application_only() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/repositories/words.py",
                "app.adapters.repositories.words",
                "import tesser.adapters as ts\n"
                "class WordsRepository(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self._rows: dict[str, str] = {}\n",
                False,
            ),
            (
                "app/adapters/repositories/__init__.py",
                "app.adapters.repositories",
                "",
                True,
            ),
            ("app/adapters/__init__.py", "app.adapters", "", True),
            (
                "app/adapters/repositories/test_words.py",
                "app.adapters.repositories.test_words",
                "import app.adapters.repositories.words as words\n"
                "import app.application.ports.words as words_port\n"
                "import app.domain.thing as thing\n"
                "import far.client.client as farclient\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "far/client/client.py",
                "far.client.client",
                "import tesser.context as ts\n"
                "class Ping(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            ("far/client/__init__.py", "far.client", "", True),
            (
                "far/domain/thing.py",
                "far.domain.thing",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
            ("far/domain/__init__.py", "far.domain", "", True),
        ))).violations()
               )
    assert any(
        "app.adapters.repositories.test_words imports app.domain.thing, but a test placed "
        "in repositories reaches only adapters.repositories, application.ports of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "app.adapters.repositories.test_words imports far.client.client, but a test placed "
        "in repositories reaches no neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_words.py:1:" in f for f in findings)
    assert not any("test_words.py:2:" in f for f in findings)


def test_a_wiring_sibling_test_mirrors_production_wiring_reach() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("app/wiring/__init__.py", "app.wiring", "", True),
            (
                "app/wiring/test_wire.py",
                "app.wiring.test_wire",
                "import app.application.service as service\n"
                "import far.client.client as farclient\n"
                "import app.domain.thing as thing\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "far/client/client.py",
                "far.client.client",
                "import tesser.context as ts\n"
                "class Ping(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            ("far/client/__init__.py", "far.client", "", True),
            (
                "far/domain/thing.py",
                "far.domain.thing",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, '_text', text)\n",
                False,
            ),
            ("far/domain/__init__.py", "far.domain", "", True),
        ))).violations()
               )
    assert any(
        "app.wiring.test_wire imports app.domain.thing, but a test placed in wiring "
        "reaches only wiring, application, adapters, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_wire.py:1:" in f for f in findings)
    assert not any("test_wire.py:2:" in f for f in findings)


def test_a_client_sibling_test_reaches_only_its_own_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/client/test_client.py",
                "app.client.test_client",
                "import app.client.client as client\n"
                "import app.domain.thing as thing\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.client.test_client imports app.domain.thing, but a test placed in client "
        "reaches only client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_client.py:1:" in f for f in findings)


def test_a_bootstrap_test_reaches_a_context_like_production_bootstrap() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "bootstrap/test_boot.py",
                "bootstrap.test_boot",
                "import app.client.client as client\n"
                "import app.domain.thing as thing\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("bootstrap/__init__.py", "bootstrap", "", True),
        ))).violations()
               )
    assert any(
        "bootstrap.test_boot imports app.domain.thing, but a test placed in "
        "bootstrap reaches a context only through its wiring, client, and adapters; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_boot.py:1:" in f for f in findings)


def test_a_protocol_test_reaches_no_context() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "protocol/test_proto.py",
                "protocol.test_proto",
                "import app.client.client as client\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("protocol/__init__.py", "protocol", "", True),
        ))).violations()
               )
    assert any(
        "protocol.test_proto imports app.client.client, but a test placed in "
        "protocol reaches no context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )


def test_a_test_that_resolves_to_no_tier_is_itself_a_finding() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/test_flat.py",
                "app.adapters.test_flat",
                "def test_x() -> None:\n    assert True\n",
                False,
            ),
            (
                "app/adapters/blobs/test_blob.py",
                "app.adapters.blobs.test_blob",
                "def test_x() -> None:\n    assert True\n",
                False,
            ),
            ("app/adapters/blobs/__init__.py", "app.adapters.blobs", "", True),
            ("app/adapters/__init__.py", "app.adapters", "", True),
        ))).violations()
               )
    assert any(
        "app.adapters.test_flat resolves to no test tier; "
        "a sibling test lives in a role package or an adapter kind package "
        "(handlers, gateways, repositories)" in f
        for f in findings
    )
    assert any(
        "app.adapters.blobs.test_blob resolves to no test tier; "
        "a sibling test lives in a role package or an adapter kind package "
        "(handlers, gateways, repositories)" in f
        for f in findings
    )


def test_a_context_tier_test_reaches_its_whole_context_and_a_neighbours_application() -> None:
    context = (
        (
            "near/domain/thing.py",
            "near.domain.thing",
            "import tesser.domain as ts\n"
            "class Tag(ts.ValueObject):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        object.__setattr__(self, '_text', text)\n",
            False,
        ),
        (
            "near/client/client.py",
            "near.client.client",
            "import tesser.context as ts\n"
            "class Client(ts.Client):\n"
            "    ...\n",
            False,
        ),
        ("near/domain/__init__.py", "near.domain", "", True),
        ("near/client/__init__.py", "near.client", "", True),
        (
            "near/tests/test_wiring.py",
            "near.tests.test_wiring",
            "import tesser.testing as ts\n"
            "import near.domain.thing as thing\n"
            "import app.application.service as neighbour\n"
            "def test_x() -> None:\n"
            "    assert True\n",
            False,
        ),
    )
    empty = (("near/tests/__init__.py", "near.tests", "", True),)
    assert not any(
        "near.tests.test_wiring" in f for f in tuple(
                                                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                                                   for v in checks.Codebase(_spec(sources=empty + context)).violations()
                                               )
    )

    declared = (("near/tests/__init__.py", "near.tests", "X = 1\n", True),)
    assert any(
        "near.tests __init__ declares code; a context tests __init__ is empty" in f
        for f in tuple(
                     f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                     for v in checks.Codebase(_spec(sources=declared + context)).violations()
                 )
    )

    helpers = (("near/tests/helpers.py", "near.tests.helpers", "VALUE = 1\n", False),)
    assert any(
        "near.tests.helpers is neither a test module nor conftest; "
        "a context tests package holds only test modules and conftest" in f
        for f in tuple(
                     f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                     for v in checks.Codebase(_spec(sources=empty + context + helpers)).violations()
                 )
    )


def test_a_root_test_reaches_a_context_only_through_wiring_and_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/wiring/wire.py",
                "app.wiring.wire",
                "import tesser.context as ts\n",
                False,
            ),
            (
                "tests/test_app.py",
                "tests.test_app",
                "import app.client.client as client\n"
                "import app.wiring.wire as wire\n"
                "import app.domain.thing as thing\n"
                "import app.application.service as service\n"
                "import bootstrap.wire\n"
                "import tests.support\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "tests/support.py",
                "tests.support",
                "import app.domain.thing as thing\n",
                False,
            ),
            ("bootstrap/wire.py", "bootstrap.wire", "", False),
        ))).violations()
               )
    reach = (
        "reaches a context only through its wiring and client; "
        "a test reaches only what its placement allows"
    )
    assert any(
        "tests.test_app imports app.domain.thing, but a test placed in "
        "the root tests package reaches a context only through its wiring and client; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "tests.test_app imports app.application.service" in f and reach in f for f in findings
    )
    assert not any("tests.test_app imports app.client.client" in f for f in findings)
    assert not any("tests.test_app imports app.wiring.wire" in f for f in findings)
    assert not any("tests.test_app imports bootstrap.wire" in f for f in findings)
    assert not any("tests.test_app imports tests.support" in f for f in findings)
    assert any(
        "tests.support is neither a test module nor conftest" in f for f in findings
    )
    assert any(
        f"tests.support imports app.domain.thing, but a test placed in the root tests package {reach}" in f
        for f in findings
    )


def test_a_placed_test_reaches_the_app_shell_only_where_its_placement_does() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/test_thing.py",
                "app.domain.test_thing",
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "srv/test_host.py",
                "srv.test_host",
                "import bootstrap.wire\n"
                "import tests.test_root\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "tests/test_root.py",
                "tests.test_root",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "bootstrap/test_wire.py",
                "bootstrap.test_wire",
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            ("srv/http.py", "srv.http", "", False),
            ("bootstrap/wire.py", "bootstrap.wire", "", False),
        ))).violations()
               )
    clause = "does not reach that package; a test reaches only what its placement allows"
    assert any(
        "app.domain.test_thing imports srv.http, but a test placed in domain "
        "does not reach that package; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("srv.test_host imports bootstrap.wire" in f for f in findings)
    assert any(
        "srv.test_host imports tests.test_root, but a test placed in srv "
        "does not reach that package" in f
        for f in findings
    )
    assert any(
        f"bootstrap.test_wire imports srv.http, but a test placed in bootstrap {clause}" in f
        for f in findings
    )


def test_a_context_tests_module_reaches_its_own_tests_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("app/tests/__init__.py", "app.tests", "", True),
            (
                "app/tests/test_thing.py",
                "app.tests.test_thing",
                "import app.tests.conftest as helpers\n"
                "import two.tests.test_two as foreign\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            ("app/tests/conftest.py", "app.tests.conftest", "", False),
            (
                "two/client/client.py",
                "two.client.client",
                "import tesser.context as ts\n",
                False,
            ),
            ("two/tests/__init__.py", "two.tests", "", True),
            (
                "two/tests/test_two.py",
                "two.tests.test_two",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.tests.test_thing imports app.tests.conftest" in f for f in findings)
    assert any(
        "app.tests.test_thing imports two.tests.test_two, but a test placed in tests "
        "reaches only application, client of a neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )


def test_an_unplaced_test_module_is_still_governed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "weird/test_nested.py",
                "weird.test_nested",
                "import app.domain.thing as thing\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "test_solo.py",
                "test_solo",
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "weird.test_nested resolves to no test tier; "
        "a sibling test lives in a role package or an adapter kind package "
        "(handlers, gateways, repositories)" in f
        for f in findings
    )
    assert any("test_solo resolves to no test tier" in f for f in findings)


def test_a_conftest_off_the_tier_map_is_a_leaf() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/adapters/conftest.py",
                "app.adapters.conftest",
                "import os\nimport app.domain.thing\n",
                False,
            ),
            (
                "app/conftest.py",
                "app.conftest",
                "import app.domain.thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.adapters.conftest imports app.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert any(
        "app.conftest imports app.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert not any("app.adapters.conftest resolves to no test tier" in f for f in findings)
    assert not any("app.adapters.conftest imports os" in f for f in findings)


def test_a_placed_conftest_carries_its_tier() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/conftest.py",
                "tests.conftest",
                "import bootstrap.wire\nimport app.domain.thing\n",
                False,
            ),
            ("app/tests/__init__.py", "app.tests", "", True),
            (
                "app/tests/conftest.py",
                "app.tests.conftest",
                "import app.domain.thing as thing\nimport srv.http\n",
                False,
            ),
            ("bootstrap/wire.py", "bootstrap.wire", "", False),
            ("srv/http.py", "srv.http", "", False),
        ))).violations()
               )
    assert any(
        "tests.conftest imports app.domain.thing, but a test placed in "
        "the root tests package reaches a context only through its wiring and client; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("tests.conftest imports bootstrap.wire" in f for f in findings)
    assert not any("app.tests.conftest imports app.domain.thing" in f for f in findings)
    assert any(
        "app.tests.conftest imports srv.http, but a test placed in tests "
        "does not reach that package" in f
        for f in findings
    )


def test_adapter_kind_and_protocol_tests_shell_reach() -> None:
    kinds = ("handlers", "gateways", "repositories")
    adapters = tuple(
        entry
        for kind in kinds
        for entry in (
            (f"app/adapters/{kind}/__init__.py", f"app.adapters.{kind}", "", True),
            (
                f"app/adapters/{kind}/test_{kind}.py",
                f"app.adapters.{kind}.test_{kind}",
                "import protocol.http as http\n"
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        )
    )
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/http.py", "protocol.http", "import tesser.srv as ts\n", False),
            ("srv/http.py", "srv.http", "", False),
        )
        + adapters
        + (
            (
                "protocol/test_http.py",
                "protocol.test_http",
                "import protocol.http as http\n"
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "app.adapters.handlers.test_handlers imports protocol.http" in f
        for f in findings
    ), f"a handlers-tier test was denied protocol: {findings}"
    for kind in ("gateways", "repositories"):
        assert any(
            f"app.adapters.{kind}.test_{kind} imports protocol.http" in f
            and "does not reach that package" in f
            for f in findings
        ), f"a {kind} test reached protocol; only srv and handlers speak protocol: {findings}"
    for kind in ("handlers", "gateways", "repositories"):
        assert any(
            f"app.adapters.{kind}.test_{kind} imports srv.http" in f
            and "does not reach that package; "
            "a test reaches only what its placement allows" in f
            for f in findings
        )
    assert not any("protocol.test_http imports protocol.http" in f for f in findings)
    assert any(
        "protocol.test_http imports srv.http, but a test placed in protocol "
        "does not reach that package" in f
        for f in findings
    )


def test_an_eval_in_a_gateway_reaches_no_shell_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/http.py", "protocol.http", "import tesser.srv as ts\n", False),
            ("srv/http.py", "srv.http", "", False),
            ("app/adapters/gateways/__init__.py", "app.adapters.gateways", "", True),
            (
                "app/adapters/gateways/eval_model.py",
                "app.adapters.gateways.eval_model",
                "import protocol.http as http\n"
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.adapters.gateways.eval_model imports protocol.http" in f
        and "does not reach that package" in f
        for f in findings
    ), f"a gateway eval reached protocol; only srv and handlers speak protocol: {findings}"
    assert any(
        "app.adapters.gateways.eval_model imports srv.http, but a test placed in gateways "
        "does not reach that package" in f
        for f in findings
    )


def test_a_context_tests_helper_answers_for_its_imports() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("app/tests/__init__.py", "app.tests", "", True),
            (
                "app/tests/support.py",
                "app.tests.support",
                "import app.domain.thing as thing\nimport srv.http\n",
                False,
            ),
            ("srv/http.py", "srv.http", "", False),
        ))).violations()
               )
    assert any(
        "app.tests.support is neither a test module nor conftest" in f for f in findings
    )
    assert any(
        "app.tests.support imports srv.http, but a test placed in tests "
        "does not reach that package" in f
        for f in findings
    )
    assert not any("app.tests.support imports app.domain.thing" in f for f in findings)


def test_a_main_below_the_context_root_is_a_governed_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/__main__.py",
                "app.domain.__main__",
                "import app.application.service as service\n",
                False,
            ),
            ("app/tests/__init__.py", "app.tests", "", True),
            (
                "app/tests/__main__.py",
                "app.tests.__main__",
                "import app.application.service as service\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.domain.__main__ imports app.application.service; the same-context matrix is" in f
        for f in findings
    )
    assert any(
        "app.tests.__main__ is neither a test module nor conftest" in f for f in findings
    )


def test_every_test_tier_has_a_shell_row() -> None:
    tiers = (
        set(checks.TEST_TIER_REACH)
        | {checks.SRV_TIER, checks.BOOTSTRAP_TIER, checks.PROTOCOL_TIER, checks.APP_TIER}
    )
    assert tiers <= set(checks.TEST_TIER_SHELL)


def test_test_module_tesser_import_rules() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_imports.py",
                "app.test_imports",
                "import tesser.domain as ts\n"
                "import tesser.testing as th\n"
                "import tesser.testing as ts2\n"
                "def test_nothing() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "app/test_fromform.py",
                "app.test_fromform",
                "from tesser.testing import fake\n"
                "def test_nothing() -> None:\n"
                "    assert fake is not None\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.test_imports imports tesser.domain; a test module's tesser imports "
        "are tesser.testing, tesser.errors, tesser.lifecycle, "
        "and tesser.serialization" in f
        for f in findings
    )
    assert any(
        "app.test_imports imports tesser.testing without the ts alias; "
        "a test module imports tesser.testing at most once, as ts" in f
        for f in findings
    )
    assert any(
        "app.test_imports imports tesser.testing again; "
        "a test module imports tesser.testing at most once, as ts" in f
        for f in findings
    )
    assert any(
        "app.test_fromform imports names from tesser.testing; "
        "a test module imports tesser.testing at most once, as ts" in f
        for f in findings
    )


def test_a_test_module_may_omit_tesser_testing() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_bare.py",
                "tests.test_bare",
                "def test_bare() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert not any("test_bare" in f for f in findings)


def test_test_module_totality_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_junk.py",
                "app.test_junk",
                "import tesser.testing as th\n"
                "def build() -> None:\n"
                "    return None\n"
                "class Junk:\n"
                "    pass\n"
                "@th.fake\n"
                "class FakeNothing:\n"
                "    pass\n"
                "COUNT = 2\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "test_junk.build" in f and "a test module holds tests, @ts.helper builders, and @ts.fake doubles" in f
        for f in findings
    )
    assert any("test_junk.Junk" in f and "a test double declares itself with @ts.fake" in f for f in findings)
    assert any("test_junk.FakeNothing" in f and "a fake implements the port or client it doubles" in f for f in findings)
    assert any(
        "test_junk" in f and "a test module holds only imports, tests, helpers, and fakes" in f
        for f in findings
    )


def test_helper_rules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/test_helpers.py",
                "app.test_helpers",
                "import tesser.testing as th\n"
                "from app.domain.thing import Thing, ThingSpec\n"
                "@th.helper\n"
                "def bad_builder(thing: Thing, count: int) -> Thing:\n"
                "    if count:\n"
                "        return thing\n"
                "    return thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "bad_builder" in f and "parameter 'thing' is not a primitive; a helper takes only defaulted primitives" in f
        for f in findings
    )
    assert any(
        "bad_builder" in f and "parameter 'count' has no default; a helper takes only defaulted primitives" in f
        for f in findings
    )
    assert any("bad_builder" in f and "does not return a ts.Spec; a helper builds a spec" in f for f in findings)
    assert any("bad_builder" in f and "has control flow" in f and "a helper only constructs" in f for f in findings)


def test_a_fake_may_implement_a_protocol_port() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "protocol/box.py",
                "protocol.box",
                "from typing import Protocol\n"
                "import tesser.srv as ts\n"
                "class BoxDoor(ts.Port, Protocol):\n"
                "    def __call__(self) -> None: ...\n",
                False,
            ),
            (
                "app/test_doors.py",
                "app.test_doors",
                "import tesser.testing as ts\n"
                "from protocol.box import BoxDoor\n"
                "@ts.fake\n"
                "class FakeDoor(BoxDoor):\n"
                "    def __call__(self) -> None:\n"
                "        return None\n"
                "def test_door() -> None:\n"
                "    assert FakeDoor\n",
                False,
            ),
        ))).violations()
               )
    assert not any("app.test_doors.FakeDoor" in f for f in findings)


def test_a_test_module_may_from_import_tesser_serialization() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/test_thing.py",
                "app.domain.test_thing",
                "from tesser.serialization import canonical_str\n"
                "def test_canonical() -> None:\n"
                '    assert canonical_str("x") == "x"\n',
                False,
            ),
        ))).violations()
               )
    assert not any("app.domain.test_thing" in f for f in findings)


def test_comments_docstrings_and_bare_strings_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_prose.py",
                "tests.test_prose",
                '"""A docstring."""\n'
                "# a prose comment\n"
                "x: int = 1  # type: ignore\n"
                "def test_ok() -> None:\n"
                "    y = 1\n"
                '    "a bare string"\n'
                "    assert y\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "test_prose.py:1: TB020" in f and "carries a docstring; "
        "code speaks for itself — comments, docstrings, and loose strings "
        "belong in the doc layer" in f
        for f in findings
    )
    assert any("test_prose.py:2: TB020" in f and "carries a code comment" in f for f in findings)
    assert any(
        "test_prose.py:6: TB020" in f and "carries a bare string statement" in f
        for f in findings
    )
    assert not any("test_prose.py:3:" in f and "TB020" in f for f in findings)


def test_the_retired_category_marker_is_an_ordinary_comment() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_marked.py",
                "tests.test_marked",
                "# tesser-category: spec\n"
                "def test_ok() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "test_marked.py:1: TB020" in f and "carries a code comment" in f for f in findings
    )


def test_mocking_library_and_patcher_fixtures_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_mocky.py",
                "tests.test_mocky",
                "from unittest.mock import patch\n"
                "import pytest\n"
                "def test_a(monkeypatch: pytest.MonkeyPatch) -> None:\n"
                "    assert patch\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "test_mocky.py:1: TB030" in f and "imports a mocking library; a test double is "
        "a hand-written fake, never a mocking library or a runtime patcher" in f
        for f in findings
    )
    assert any(
        "test_mocky.py:3: TB030" in f and "takes the monkeypatch fixture" in f
        for f in findings
    )
    assert any(
        "test_mocky.py:3: TB030" in f and "reaches for pytest MonkeyPatch" in f
        for f in findings
    )


def test_a_marked_patcher_seam_is_suppressed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_seam.py",
                "tests.test_seam",
                "def test_a(monkeypatch) -> None:  # tessercheck:ignore TB030\n"
                "    assert monkeypatch\n",
                False,
            ),
        ))).violations()
               )
    assert not any("test_seam" in f for f in findings)


def test_a_called_shadowed_builtin_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_shadow.py",
                "tests.test_shadow",
                "def test_a() -> None:\n"
                "    id = 'x'\n"
                "    assert id(3)\n"
                "def test_b(len: int = 0) -> None:\n"
                "    assert len == 0\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "test_shadow.py:3: TB033" in f and "binds id and calls it in the same scope; "
        "a shadowed builtin is never called — rename the binding" in f
        for f in findings
    )
    assert not any("test_shadow.py:5:" in f and "TB033" in f for f in findings)


def test_string_form_equality_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/test_streq.py",
                "tests.test_streq",
                "def test_a() -> None:\n"
                "    a, b = 1, 2\n"
                "    assert str(a) == str(b)\n"
                "    assert str(a) == 'one'\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "test_streq.py:3: TB004" in f and "compare value objects by value, "
        "never by their string form" in f
        for f in findings
    )
    assert not any("test_streq.py:4:" in f for f in findings)


def test_a_value_object_mutable_collection_field_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/bag.py",
                "app.domain.bag",
                "import tesser.domain as ts\n"
                "class Bag(ts.ValueObject):\n"
                "    _items: list[str]\n"
                "    _names: tuple[str, ...]\n"
                "    def __init__(self, item: str) -> None:\n"
                "        object.__setattr__(self, '_items', [item])\n"
                "        object.__setattr__(self, '_names', (item,))\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "bag.py:3: TB002" in f and "field _items is a mutable collection; "
        "a value object's field is hashable — a tuple or frozenset, never "
        "a mutable collection" in f
        for f in findings
    )
    assert not any("_names" in f and "TB002" in f for f in findings)


def test_mutable_set_and_quoted_annotations_are_still_mutable_collections() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/holder.py",
                "app.domain.holder",
                "import tesser.domain as ts\n"
                "from typing import MutableSet\n"
                "class Holder(ts.ValueObject):\n"
                "    _mset: MutableSet[str]\n"
                "    _quoted: 'list[str]'\n"
                "    def __init__(self, item: str) -> None:\n"
                "        object.__setattr__(self, '_mset', {item})\n"
                "        object.__setattr__(self, '_quoted', [item])\n",
                False,
            ),
        ))).violations()
               )
    assert any("field _mset is a mutable collection" in f for f in findings)
    assert any("field _quoted is a mutable collection" in f for f in findings)


def test_a_value_object_hides_its_representation() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/leaky.py",
                "app.domain.leaky",
                "import tesser.domain as ts\n"
                "class Leaky(ts.ValueObject):\n"
                "    amount: int\n"
                "    _kept: int\n"
                "    def __init__(self, amount: int) -> None:\n"
                "        object.__setattr__(self, 'amount', amount)\n"
                "        object.__setattr__(self, '_kept', amount)\n"
                "    def kept(self) -> int:\n"
                "        return self._kept\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "leaky.py:3: TB010" in f and "exposes field amount; a value object hides its "
        "representation — a public field belongs on a spec" in f
        for f in findings
    )
    assert any(
        "TB010" in f and "Leaky.kept passes the raw primitive through; "
        "a value object's accessor returns a value object — "
        "the canonical exit is the only primitive door" in f
        for f in findings
    )


def test_an_accessor_never_hands_back_the_backing_collection() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/box.py",
                "app.domain.box",
                "import tesser.domain as ts\n"
                "class BoxSpec(ts.Spec):\n"
                "    def __init__(self, item: str) -> None:\n"
                "        self.item = item\n"
                "class Box(ts.AggregateRoot):\n"
                "    _items: list[str]\n"
                "    def __init__(self, spec: BoxSpec) -> None:\n"
                "        self._items = [spec.item]\n"
                "    def items(self) -> list[str]:\n"
                "        return self._items\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "TB011" in f and "Box.items hands back its backing collection; an accessor "
        "returns a defensive copy, never the backing store" in f
        for f in findings
    )


def test_an_aggregate_is_referenced_by_id_never_held() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/pair.py",
                "app.domain.pair",
                "import tesser.domain as ts\n"
                "import app.domain.thing as thing\n"
                "class PairSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class Pair(ts.AggregateRoot):\n"
                "    _other: thing.Thing\n"
                "    def __init__(self, spec: PairSpec) -> None:\n"
                "        self._other = thing.Thing(thing.ThingSpec(text=spec.text))\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "TB012" in f and "Pair field _other holds another aggregate root; an aggregate "
        "is referenced by its ID value object, never held" in f
        for f in findings
    )


def test_exit_norms_leaf_and_structured() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/exits.py",
                "app.domain.exits",
                "import tesser.domain as ts\n"
                "@ts.function\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n"
                "class GoodLeaf(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n"
                "class WrongExit(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __int__(self) -> int:\n"
                "        return 0\n"
                "class HandRolled(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return self._value.upper()\n"
                "class Compound(ts.ValueObject):\n"
                "    _a: GoodLeaf\n"
                "    _b: GoodLeaf\n"
                "    def __init__(self, a: str, b: str) -> None:\n"
                "        object.__setattr__(self, '_a', GoodLeaf(a))\n"
                "        object.__setattr__(self, '_b', GoodLeaf(b))\n"
                "    def __str__(self) -> str:\n"
                "        return 'x'\n",
                False,
            ),
        ))).violations()
               )
    assert not any("GoodLeaf" in f and "TB015" in f for f in findings)
    assert not any("GoodLeaf" in f and "TB018" in f for f in findings)
    assert any(
        "TB015" in f and "WrongExit.__int__ is a mismatched exit; a leaf defines exactly "
        "its backing type's conversion dunder" in f
        for f in findings
    )
    assert any(
        "TB018" in f and "HandRolled.__str__ hand-rolls its exit; a canonical exit is a "
        "one-line delegation to its canonical_* policy" in f
        for f in findings
    )
    assert any(
        "TB015" in f and "Compound.__str__ is a primitive exit; a structured domain "
        "object has no primitive exit — decompose through leaf components" in f
        for f in findings
    )


def test_composition_norms() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/shapes.py",
                "app.domain.shapes",
                "import tesser.domain as ts\n"
                "class Flag(ts.ValueObject):\n"
                "    _value: bool\n"
                "    def __init__(self, value: bool) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "class Mixed(ts.ValueObject):\n"
                "    _raw: str\n"
                "    _on: bool\n"
                "    def __init__(self, raw: str, on: bool) -> None:\n"
                "        object.__setattr__(self, '_raw', raw)\n"
                "        object.__setattr__(self, '_on', on)\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "TB016" in f and "Flag field _value is a bool; bool and complex are not "
        "value-object material — model the raw value or reach for an enum" in f
        for f in findings
    )
    assert any(
        "TB016" in f and "Mixed field _raw is a bare primitive; a compound backs "
        "itself with child value objects" in f
        for f in findings
    )
    assert any("TB016" in f and "Mixed field _on is a bool" in f for f in findings)


def test_a_value_object_has_one_construction_door() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/doors.py",
                "app.domain.doors",
                "import tesser.domain as ts\n"
                "@ts.function\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n"
                "class Slug(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n"
                "    @classmethod\n"
                "    def parse(cls, raw: str) -> 'Slug':\n"
                "        return cls(raw.strip())\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "TB017" in f and "Slug.parse is a second construction door; a value object has "
        "one door — its own __init__" in f
        for f in findings
    )


def test_domain_returns_and_spec_returns() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/returns.py",
                "app.domain.returns",
                "import tesser.domain as ts\n"
                "class WidgetSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class Widget(ts.Entity):\n"
                "    def __init__(self, spec: WidgetSpec) -> None:\n"
                "        self._text = spec.text\n"
                "    def label(self) -> str:\n"
                "        return self._text.upper()\n"
                "    def snapshot(self) -> WidgetSpec:\n"
                "        return WidgetSpec(text=self._text)\n"
                "    def touch(self) -> None:\n"
                "        return None\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "TB019" in f and "Widget.label returns str; a domain object's public behavior "
        "hands back domain objects — the licensed exits are the protocol dunders, "
        "the canonical exit, and a -> None transition" in f
        for f in findings
    )
    assert any(
        "TB015" in f and "Widget.snapshot returns a spec; a domain object never "
        "serializes itself — a spec is construction data, not an exit" in f
        for f in findings
    )
    assert not any("Widget.touch" in f for f in findings)


def test_review_pins_for_the_shape_norms() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/pins.py",
                "app.domain.pins",
                "import tesser.domain as ts\n"
                "from typing import ClassVar, Self\n"
                "@ts.function\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n"
                "class SelfDoor(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n"
                "    @classmethod\n"
                "    def parse(cls, raw: str) -> Self:\n"
                "        return cls(raw)\n"
                "    @classmethod\n"
                "    def bare_door(cls, raw):  # type: ignore[no-untyped-def]\n"
                "        return cls(raw)\n"
                "    @classmethod\n"
                "    def kind(cls) -> type['SelfDoor']:\n"
                "        return cls\n"
                "class Quoted(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n"
                "    def label(self) -> 'str':\n"
                "        return self._value.upper()\n"
                "class Marked(ts.ValueObject):\n"
                "    _kinds: ClassVar[tuple[str, ...]] = ()\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n",
                False,
            ),
        ))).violations()
               )
    assert any("SelfDoor.parse is a second construction door" in f for f in findings)
    assert any("SelfDoor.bare_door is a second construction door" in f for f in findings)
    assert not any("SelfDoor.kind" in f for f in findings)
    assert any(
        "Quoted.label returns str" in f and "TB019" in f for f in findings
    )
    assert not any("Marked" in f for f in findings)


def test_module_qualified_canonical_delegation_passes() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/policy.py",
                "app.domain.policy",
                "import tesser.domain as ts\n"
                "@ts.function\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n",
                False,
            ),
            (
                "app/domain/word.py",
                "app.domain.word",
                "import tesser.domain as ts\n"
                "import app.domain.policy as policy\n"
                "class Word(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "    def __str__(self) -> str:\n"
                "        return policy.canonical_str(self._value)\n",
                False,
            ),
        ))).violations()
               )
    assert not any("Word" in f for f in findings)


def test_undeclared_backing_collection_is_still_caught() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/sack.py",
                "app.domain.sack",
                "import tesser.domain as ts\n"
                "class SackSpec(ts.Spec):\n"
                "    def __init__(self, item: str) -> None:\n"
                "        self.item = item\n"
                "class Sack(ts.AggregateRoot):\n"
                "    def __init__(self, spec: SackSpec) -> None:\n"
                "        self._items = [spec.item]\n"
                "    def items(self) -> list[str]:\n"
                "        return self._items\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "TB011" in f and "Sack.items hands back its backing collection" in f
        for f in findings
    )


def test_an_ignore_suppresses_exactly_its_finding() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(("stray.py", "stray", "import os  # tessercheck:ignore TB040\n", False),))).violations()
               )
    assert not any("stray" in f for f in findings)


def test_a_scoped_ignore_leaves_other_codes_alone() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(("stray.py", "stray", "import os  # tessercheck:ignore TB050\n", False),))).violations()
               )
    assert any(
        "stray belongs to no governed package" in f and " TB040 " in f for f in findings
    )
    assert any(
        "stray.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )


def test_a_stale_ignore_is_itself_a_finding() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/extra.py",
                "app.domain.extra",
                "import tesser.domain as ts  # tessercheck:ignore\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app/domain/extra.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )


def test_a_file_level_ignore_covers_the_whole_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/host.py",
                "srv.host",
                "# tessercheck:ignore-file TB050\nimport os\n",
                False,
            ),
        ))).violations()
               )
    assert not any("never imports tesser.srv" in f for f in findings)
    assert not any("TB090" in f and "srv/host.py" in f for f in findings)


def test_a_marker_suppresses_several_codes_space_or_comma_separated() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("stray.py", "stray", "import os  # tessercheck:ignore TB040 TB050\n", False),
            ("loose.py", "loose", "import os  # tessercheck:ignore TB040, TB050\n", False),
        ))).violations()
               )
    assert not any("stray" in f for f in findings)
    assert not any("loose" in f for f in findings)


def test_a_file_level_ignore_requires_codes() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(("stray.py", "stray", "import os  # tessercheck:ignore-file\n", False),))).violations()
               )
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("stray.py:1: TB090" in f for f in findings)


def test_a_typo_or_junk_token_makes_the_marker_inert() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("stray.py", "stray", "import os  # tessercheck:ignored TB040\n", False),
            (
                "loose.py",
                "loose",
                "import os  # tessercheck:ignore TB040 permanent\n",
                False,
            ),
            ("bracket.py", "bracket", "import os  # tessercheck:ignore [TB040]\n", False),
        ))).violations()
               )
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("loose belongs to no governed package" in f for f in findings)
    assert any("bracket belongs to no governed package" in f for f in findings)
    assert not any("stray.py" in f and "TB090" in f for f in findings)
    assert any("loose.py:1: TB090" in f for f in findings)
    assert any("bracket.py:1: TB090" in f for f in findings)


def test_a_bare_line_ignore_is_line_scoped() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/extra.py",
                "app.domain.extra",
                "import os\nimport tesser.domain as ts  # tessercheck:ignore\n",
                False,
            ),
        ))).violations()
               )
    assert any("app.domain.extra imports os" in f and " TB062 " in f for f in findings)
    assert any("app/domain/extra.py:2: TB090" in f for f in findings)


def test_tb090_itself_cannot_be_ignored() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/domain/extra.py",
                "app.domain.extra",
                "import tesser.domain as ts  # tessercheck:ignore-file TB090\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app/domain/extra.py:1: TB090" in f
        and "an ignore comment suppresses an actual finding" in f
        for f in findings
    )


def test_a_colliding_module_definition_is_a_finding_not_a_crash() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("col.py", "col", "import tesser.srv as ts\n", False),
            ("col/__init__.py", "col", "", True),
        ))).violations()
               )
    assert any(
        "col.py:1: TB043" in f and "a module has one definition" in f for f in findings
    )
    assert any(
        "col/__init__.py:1: TB043" in f and "a module has one definition" in f
        for f in findings
    )


def test_an_unparseable_module_is_a_finding_not_a_crash() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(("broken.py", "broken", "def f(:\n", False),))).violations()
               )
    assert any(
        "broken.py:1: TB043" in f and "every checked module parses" in f for f in findings
    )
    assert any("app/domain/thing.py" not in f for f in findings)


def test_a_non_utf8_file_is_a_finding_not_a_crash() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(("binary.py", "binary", None, False),))).violations()
               )
    assert any(
        "binary.py:1: TB043" in f and "every checked module is readable UTF-8 Python" in f
        for f in findings
    )


def test_a_colliding_unparseable_file_reports_the_collision() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("col.py", "col", "def f(:\n", False),
            ("col/__init__.py", "col", "", True),
        ))).violations()
               )
    assert any(
        "col.py:1: TB043" in f and "a module has one definition" in f for f in findings
    )
    assert not any("every checked module parses" in f for f in findings)


def test_reader_findings_are_never_inline_suppressible() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "broken.py",
                "broken",
                "# tessercheck:ignore-file TB043\ndef f(:\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "broken.py:2: TB043" in f and "every checked module parses" in f for f in findings
    )
    assert not any("TB090" in f for f in findings)


def test_ports_is_a_package_never_a_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/application/ports.py",
                "app.application.ports",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.application.ports is a ports module; ports is a package, never a module" in f
        for f in findings
    )


def test_a_ports_init_is_empty() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/application/ports/__init__.py",
                "app.application.ports",
                "X = 1\n",
                True,
            ),
        ))).violations()
               )
    assert any(
        "app.application.ports __init__ declares code; a ports __init__ is empty" in f
        for f in findings
    )


def test_a_ports_module_is_a_leaf() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink imports socket; a ports module imports "
        "only tesser.application and the pure stdlib" in f
        for f in findings
    )
    assert not any("imports enum;" in f for f in findings)


def test_a_ports_module_tesser_import_rules() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink has a loose module-level statement; "
        "a ports module holds only imports and classes" in f
        for f in findings
    )


def test_a_ports_module_declares_exactly_one_port() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.adapters.gateways.memory imports app.application.service; "
        "the same-context matrix is a role to itself, application to domain and client, "
        "adapters to application/ports, wiring to application, adapters, and client" in f
        for f in findings
    )
    assert not any("imports app.application.ports.sink;" in f for f in findings)


def test_a_port_dto_field_is_never_a_union() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.FindResponse.__init__ field 'item' is a union; "
        "a port DTO field is never a union, optional included — model the outcome as an enum" in f
        for f in findings
    )


def test_a_client_dto_field_may_still_be_optional() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert not any("app.client.optional" in f and "is a union" in f for f in findings)


def test_a_conforming_ports_module_is_silent() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert not any("app/application/ports/sink.py" in f for f in findings), (
        f"a conforming ports module produced findings: "
        f"{[f for f in findings if 'ports/sink.py' in f]}"
    )


def test_a_ports_package_holds_only_ports_modules() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.test_support is not a ports module; a ports package holds "
        "only ports modules, and test_/eval_/conftest are reserved names, because a fake "
        "here would be an implementation adapters may import" in f
        for f in findings
    ), f"a fake could live in the package adapters may import: {findings}"
    assert any("app.application.ports.conftest is not a ports module" in f for f in findings)


def test_a_client_dto_with_a_sibling_enum_stays_strict() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.client.verdict.VerdictResponse.__init__ parameter 'verdict' is not allowed; "
        "a DTO field is a primitive or another DTO" in f
        for f in findings
    )


def test_a_port_dto_field_is_never_a_bare_bool() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.FlagResponse.__init__ field 'found' is a bool; "
        "a port DTO field is never a bare bool — model the outcome as an enum" in f
        for f in findings
    )
    assert not any("'outcome'" in f for f in findings)


def test_a_port_dto_is_never_subclassed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.FoundItem subclasses a port DTO; a port DTO is never "
        "subclassed, because a response hierarchy is a union mypy cannot check for exhaustiveness" in f
        for f in findings
    )


def test_a_port_method_shape_survives_async_and_dunder_call() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert not any("save_count" in f for f in findings), (
        f"a fake's inspection method was flagged as a port method: "
        f"{[f for f in findings if 'save_count' in f]}"
    )


def test_a_ports_enum_is_a_plain_enum() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Loose is an enum.StrEnum; a ports enum is an enum.Enum, "
        "because a str- or int-backed member compares equal to a raw literal "
        "and reopens the typo the enum closes" in f
        for f in findings
    )
    assert not any("Tight" in f for f in findings)


def test_a_port_method_declares_a_shape_and_never_a_body() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Sink.save carries a body; a port method declares a shape "
        "and never a body, because a ports module holds no logic to import" in f
        for f in findings
    )
    assert not any("Sink.drop" in f for f in findings)


def test_an_ignored_ports_file_is_still_governed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports imports app.domain.thing; a ports module is a leaf" in f
        for f in findings
    ), f"an ignored TB041 unlocked the module: {findings}"
    assert any("declares 2 ports" in f for f in findings)
    assert any("app.application.ports.Leaked is a service" in f for f in findings)


def test_an_enum_base_cannot_hide_a_second_port() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any("declares 2 ports" in f for f in findings), (
        f"an enum base hid a second port, so two ports could share every DTO: {findings}"
    )


def test_an_enum_is_resolved_by_its_binding_not_its_spelling() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.masked.Rules declares no ts.* base" in f for f in findings
    ), f"a name bound to something else was accepted as an enum: {findings}"
    assert not any("aliased.Outcome" in f for f in findings), (
        f"a properly bound enum alias was rejected: {findings}"
    )


def test_a_dynamic_import_is_not_a_way_around_the_matrix() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.adapters.gateways.memory imports dynamically through importlib.import_module; "
        "an import is a statement the walk can read, never a call" in f
        for f in findings
    ), f"importlib walked around the import matrix: {findings}"


def test_a_dto_declares_its_fields_where_the_rules_can_read_them() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Loaded.resolve defines a method on a DTO; "
        "a DTO carries data and nothing else" in f
        for f in findings
    ), f"async def carried logic onto a DTO: {findings}"


def test_a_nested_class_cannot_hide_a_second_port() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Holder.Second is a nested class; a ports module declares "
        "its port and its DTOs at module level, where the one-port count can see them" in f
        for f in findings
    ), f"a nested class hid a second port sharing every DTO: {findings}"


def test_a_dynamic_import_is_resolved_by_binding_not_spelling() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.adapters.gateways.memory imports dynamically through importlib.import_module" in f
        for f in findings
    ), f"a from-import of import_module walked around TB068: {findings}"
    assert not any("local" in f and "TB068" in f for f in findings), (
        f"a local name spelled importlib false-positived: {findings}"
    )


def test_a_port_speaks_shapes_it_declares_itself() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Sink.bare names a shape it does not declare; a port "
        "method speaks requests and responses declared in its own ports module, never a "
        "bare ts.Request or ts.Response, which two ports would share" in f
        for f in findings
    ), f"two ports could share the base classes as their whole vocabulary: {findings}"
    assert not any("Sink.own" in f for f in findings)


def test_a_ports_class_carries_no_class_level_statement() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Sink carries a class-level statement; only an enum "
        "member is class-level data in a ports module, because anything else runs at "
        "import in the one application module adapters may import" in f
        for f in findings
    ), f"import-time execution landed in the ports leaf: {findings}"
    assert not any("Outcome" in f for f in findings), f"an enum member was flagged: {findings}"


def test_a_private_port_method_carries_no_body() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Sink._score carries a body; a port method declares a "
        "shape and never a body" in f
        for f in findings
    ), f"a private method carried logic every implementer inherits: {findings}"


def test_a_stub_cannot_shadow_the_shape_the_rules_read() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink is a stub; a module carries its own shape, because a "
        "stub is what the type checker reads and the walk cannot" in f
        for f in findings
    ), f"a stub bypassed every ports rule at the type level: {findings}"


def test_a_ports_enum_carries_nothing_but_its_members() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Outcome carries more than its members; a ports enum "
        "is a closed set of names and nothing else, because a method or a decorator here "
        "is logic every adapter imports" in f
        for f in findings
    ), f"an enum smuggled logic into the ports leaf: {findings}"
    assert not any("FOUND" in f or "NEXT" in f for f in findings)


def test_a_port_dto_constructor_only_assigns_its_parameters() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Validating.__init__ carries logic; a port DTO "
        "constructor only assigns its parameters, because a ports module holds no "
        "logic to import" in f
        for f in findings
    ), f"domain validation lived in the ports leaf: {findings}"
    assert not any("Plain" in f or "Empty" in f for f in findings)


def test_a_port_declares_only_the_calls_an_implementer_provides() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Sink.audit carries a computed default; a ports module "
        "holds no expression that runs at import, because every adapter imports it" in f
        for f in findings
    ), f"an async def default expression ran at import: {findings}"


def test_a_port_dto_binds_only_its_own_parameters() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Capability.__init__ carries logic; a port DTO "
        "constructor only assigns its parameters" in f
        for f in findings
    ), f"a DTO bound a live capability an adapter could call: {findings}"
    assert not any("Plain" in f for f in findings)


def test_a_ports_class_carries_no_keyword() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert any(
        "app.application.ports.sink.Meta carries a class keyword; a ports module holds no "
        "expression that runs at import, and a metaclass is logic every adapter imports" in f
        for f in findings
    ), f"a metaclass ran logic at import of the ports leaf: {findings}"


def test_an_enum_member_may_be_negative_or_annotated() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    assert not any("UNKNOWN" in f or "ALLOWED" in f or "NEXT" in f for f in findings), (
        f"a legitimate enum member was rejected: {findings}"
    )
    assert any(
        "app.application.ports.sink.Outcome carries more than its members" in f
        for f in findings
    ), f"a dunder assignment laundered prose past the comments norm: {findings}"


def test_a_ports_module_computes_no_annotation() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
               )
    for name in ("rebound", "indirect", "builtin", "registry"):
        assert any(f"app.adapters.gateways.{name} imports dynamically" in f for f in findings), (
            f"the {name} spelling reached application with no import edge: {findings}"
        )


def test_a_ports_module_holds_only_shapes_the_rules_can_read() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
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
        ))).violations()
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


def test_a_second_export_declaration_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False)), exports=('one', 'two'))).violations()
    )
    assert len(findings) == 1, findings
    assert any(
        "a tree has one exported kernel, so a declaration carries at most one "
        "'export <dir>' line" in f
        for f in findings
    ), findings


def test_an_export_that_is_no_package_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False)), exports=('ghost',))).violations()
    )
    assert any(
        "this tree exports 'ghost' but no such package exists; "
        "an export names a package at the tree root" in f
        for f in findings
    ), findings


def test_an_export_never_takes_a_shell_or_kernel_name() -> None:
    for taken in ("srv", "kernel", "tests", "protocol", "bootstrap"):
        findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False)), exports=(taken,))).violations()
    )
        assert any(
            "an exported kernel never takes the name of the kernel package "
            "or the app shell" in f
            for f in findings
        ), (taken, findings)


def test_kernel_is_a_package_never_a_module() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel.py', 'kernel', 'X = 1\n', False),))).violations()
    )
    assert any(
        "kernel.py:1: TB041 kernel is a kernel module at the tree root; "
        "kernel is a package, never a module" in f
        for f in findings
    ), findings


def test_a_kernel_init_only_reexports_from_its_own_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/__init__.py', 'kernel', 'import app.domain.thing as thing\nX = 1\n', True)))).violations()
    )
    assert any(
        "kernel imports app.domain.thing; "
        "a kernel __init__ only re-exports from its own kernel" in f
        for f in findings
    ), findings
    assert any(
        "kernel __init__ declares code; "
        "a kernel __init__ only re-exports from its own kernel" in f
        for f in findings
    ), findings


def test_every_kernel_class_declares_its_block() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/loose.py', 'kernel.loose', 'import tesser.domain as ts\nclass Bare:\n    pass\n', False)))).violations()
    )
    assert any(
        "kernel.loose.Bare declares no ts.* base; "
        "every kernel class declares its block" in f
        for f in findings
    ), findings


def test_a_kernel_holds_only_domain_kinds() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/svc.py', 'kernel.svc', 'import tesser.domain as ts\nimport tesser.application as tsa\nclass Svc(tsa.ApplicationService):\n    pass\n', False)))).violations()
    )
    assert any(
        "a kernel holds only domain kinds — "
        "value objects, entities, aggregates, and specs" in f
        for f in findings
    ), findings


def test_kernel_statement_totality() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/loose.py', 'kernel.loose', 'import tesser.domain as ts\nLIMIT = 3\ndef helper() -> int:\n    return LIMIT\nprint(LIMIT)\n', False)))).violations()
    )
    assert any("a kernel constant is Final" in f for f in findings), findings
    assert any(
        "a kernel function declares itself with @ts.function" in f for f in findings
    ), findings
    assert any(
        "a kernel module holds only imports, classes, declared functions, "
        "and Final constants" in f
        for f in findings
    ), findings


def test_kernel_tesser_import_rules() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/wrong.py', 'kernel.wrong', 'import tesser.adapters as ts\nclass Money(ts.ValueObject):\n    pass\n', False)))).violations()
    )
    assert any(
        "a kernel module imports only tesser.domain" in f for f in findings
    ), findings
    absent = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/bare.py', 'kernel.bare', 'from typing import Final\nLIMIT: Final[int] = 3\n', False)))).violations()
    )
    assert any(
        "a kernel module imports tesser.domain exactly once, as ts" in f
        for f in absent
    ), absent


def test_kernel_import_allowlist() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/prices.py', 'kernel.prices', 'import tesser.domain as ts\nfrom decimal import Decimal\nimport kernel.money\nimport app.domain.thing\nimport requests\nclass PriceSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False)))).violations()
    )
    assert any(
        "kernel.prices imports app.domain.thing; a kernel imports only its "
        "kernel, tesser.domain, declared kernels, and the pure stdlib" in f
        for f in findings
    ), findings
    assert any(
        "kernel.prices imports requests; a kernel imports only its "
        "kernel, tesser.domain, declared kernels, and the pure stdlib" in f
        for f in findings
    ), findings
    assert not any("imports decimal" in f for f in findings), findings
    assert not any("imports kernel.money" in f for f in findings), findings


def test_a_declared_kernel_import_is_legal_in_a_kernel() -> None:
    def grown(imports: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/prices.py', 'kernel.prices', 'import tesser.domain as ts\nimport money_kernel\nclass PriceSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False)), imports=imports)).violations()
    )

    assert not any(
        "imports money_kernel" in f for f in grown(("money_kernel",))
    ), grown(("money_kernel",))
    assert any("imports money_kernel" in f for f in grown(())), grown(())


def test_pure_roles_may_import_kernels() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('app/domain/price.py', 'app.domain.price', 'import tesser.domain as ts\nfrom kernel.money import Money\nimport money_kernel\nclass PriceSpec(ts.Spec):\n    def __init__(self, money: Money) -> None:\n        self.money = money\n', False)), imports=('money_kernel',))).violations()
    )
    assert not any("app/domain/price.py" in f for f in findings), findings


def test_an_undeclared_package_in_a_pure_role_is_still_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('app/domain/price.py', 'app.domain.price', 'import tesser.domain as ts\nimport money_kernel\nclass PriceSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False)))).violations()
    )
    assert any(
        "app.domain.price imports money_kernel; domain, client, and application "
        "import only their context, their kernels, their tesser package, "
        "and the pure stdlib" in f
        for f in findings
    ), findings


def test_a_kernel_test_reaches_only_its_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/test_money.py', 'kernel.test_money', 'import tesser.testing as ts\nfrom kernel.money import Money\nimport app.domain.thing\ndef test_money() -> None:\n    assert Money(1) == Money(1)\n', False)))).violations()
    )
    assert any(
        "kernel.test_money imports app.domain.thing, but a test placed in "
        "a kernel reaches no context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    ), findings
    assert not any("imports kernel.money" in f for f in findings), findings


def test_an_exported_kernel_is_governed_like_a_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('shells/__init__.py', 'shells', '', True), ('shells/svc.py', 'shells.svc', 'import tesser.domain as ts\nimport tesser.application as tsa\nclass Svc(tsa.ApplicationService):\n    pass\n', False), ('app/domain/price.py', 'app.domain.price', 'import tesser.domain as ts\nfrom shells.svc import Svc\nclass PriceSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False)), exports=('shells',))).violations()
    )
    assert any(
        "a kernel holds only domain kinds" in f for f in findings
    ), findings
    assert not any("app/domain/price.py" in f for f in findings), findings


def test_a_context_shaped_export_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('beta/__init__.py', 'beta', '', True), ('beta/domain/policy.py', 'beta.domain.policy', 'import tesser.domain as ts\nclass PolicySpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False)), exports=('beta',))).violations()
    )
    assert len(findings) == 1, findings
    assert any(
        "a bounded context's domain is never exported — a kernel is not a context" in f
        for f in findings
    ), findings


def test_an_import_declaration_never_names_this_tree() -> None:
    for declared in ("srv", "kernel", "tests", "app"):
        findings = tuple(
            f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
            for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False)), imports=(declared,))).violations()
        )
        assert any(
            "an import declaration names an installed external kernel, "
            "never something the walk governs" in f
            for f in findings
        ), (declared, findings)


def test_an_import_declaration_never_names_the_stdlib() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False)), imports=('subprocess', 'os.path'), stdlib=('os', 'subprocess'))).violations()
    )
    assert (
        sum(
            "the pure stdlib is already legal and the rest of it is never a kernel" in f
            for f in findings
        )
        == 2
    ), findings


def test_an_unused_import_declaration_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False)), imports=('money_kernel',))).violations()
    )
    assert any(
        "an import declaration that legalizes nothing is itself a finding" in f
        for f in findings
    ), findings


def test_kernel_siblings_import_each_other_in_both_kernel_shapes() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('shells/__init__.py', 'shells', '', True), ('shells/base.py', 'shells.base', 'import tesser.domain as ts\nclass BaseSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False), ('shells/rich.py', 'shells.rich', 'import tesser.domain as ts\nfrom shells.base import BaseSpec\nclass RichSpec(ts.Spec):\n    def __init__(self, base: BaseSpec) -> None:\n        self.base = base\n', False), ('kernel/rates.py', 'kernel.rates', 'import tesser.domain as ts\nfrom kernel.money import Money\nclass RateSpec(ts.Spec):\n    def __init__(self, money: Money) -> None:\n        self.money = money\n', False)), exports=('shells',))).violations()
    )
    assert not any("shells/rich.py" in f for f in findings), findings
    assert not any("kernel/rates.py" in f for f in findings), findings


def test_the_exported_kernel_never_imports_the_private_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('shells/__init__.py', 'shells', '', True), ('shells/base.py', 'shells.base', 'import tesser.domain as ts\nfrom kernel.money import Money\nclass BaseSpec(ts.Spec):\n    def __init__(self, money: Money) -> None:\n        self.money = money\n', False)), exports=('shells',))).violations()
    )
    assert any(
        "shells.base imports kernel.money; a kernel imports only its "
        "kernel, tesser.domain, declared kernels, and the pure stdlib" in f
        for f in findings
    ), findings


def test_a_declared_import_matches_on_the_package_boundary() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/prices.py', 'kernel.prices', 'import tesser.domain as ts\nimport money_kernel.sub\nimport money_kernel_evil\nclass PriceSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False)), imports=('money_kernel',))).violations()
    )
    assert any("imports money_kernel_evil" in f for f in findings), findings
    assert not any("imports money_kernel.sub" in f for f in findings), findings


def test_a_kernel_import_is_only_trusted_when_its_module_was_walked() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('app/domain/price.py', 'app.domain.price', 'import tesser.domain as ts\nfrom kernel.money import Money\nfrom kernel.vendored.impure import Client\nclass PriceSpec(ts.Spec):\n    def __init__(self, money: Money) -> None:\n        self.money = money\n', False)))).violations()
    )
    assert any("imports kernel.vendored.impure" in f for f in findings), findings
    assert not any("imports kernel.money" in f for f in findings), findings


def test_a_pure_role_kernel_import_needs_the_kernel_to_exist() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('app/domain/price.py', 'app.domain.price', 'import tesser.domain as ts\nfrom kernel.money import Money\nclass PriceSpec(ts.Spec):\n    def __init__(self, money: Money) -> None:\n        self.money = money\n', False),))).violations()
    )
    assert any(
        "app.domain.price imports kernel.money; domain, client, and application "
        "import only their context, their kernels, their tesser package, "
        "and the pure stdlib" in f
        for f in findings
    ), findings


def test_a_role_named_subpackage_of_the_fixed_kernel_stays_kernel_governed() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/domain/__init__.py', 'kernel.domain', '', True), ('kernel/domain/svc.py', 'kernel.domain.svc', 'import tesser.domain as ts\nimport tesser.application as tsa\nclass Svc(tsa.ApplicationService):\n    pass\n', False)))).violations()
    )
    assert any(
        "a kernel holds only domain kinds" in f for f in findings
    ), findings
    assert not any("is not a context module" in f for f in findings), findings


def test_a_kernel_init_rejects_a_near_miss_package() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/__init__.py', 'kernel', 'import kernelish.money as money\n', True), ('kernelish/__init__.py', 'kernelish', '', True), ('kernelish/money.py', 'kernelish.money', 'import app.domain.thing\n', False)))).violations()
    )
    assert any(
        "kernel imports kernelish.money; "
        "a kernel __init__ only re-exports from its own kernel" in f
        for f in findings
    ), findings


def test_a_member_form_reexport_in_a_kernel_init_is_legal() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/__init__.py', 'kernel', 'from kernel.money import Money as Money\n', True)))).violations()
    )
    assert not any("kernel/__init__.py" in f for f in findings), findings


def test_an_export_naming_a_bare_module_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('shells.py', 'shells', 'X = 1\n', False)), exports=('shells',))).violations()
    )
    assert len(findings) == 1, findings
    assert any(
        "an export names a package at the tree root" in f for f in findings
    ), findings


def test_a_kernel_test_may_reach_the_trees_other_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('shells/__init__.py', 'shells', '', True), ('shells/base.py', 'shells.base', 'import tesser.domain as ts\nclass BaseSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False), ('kernel/test_money.py', 'kernel.test_money', 'from kernel.money import Money\nfrom shells.base import BaseSpec\ndef test_money() -> None:\n    assert Money(1) == Money(1)\n', False)), exports=('shells',))).violations()
    )
    assert not any("kernel/test_money.py" in f for f in findings), findings
