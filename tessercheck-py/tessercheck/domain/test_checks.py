from __future__ import annotations

import ast
import inspect
import textwrap
import pathlib

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
    pure_stdlib: tuple[str, ...] = (),
    base: tuple[tuple[str, str, str | None, bool], ...] = (
        (
            "shop/domain/thing.py",
            "shop.domain.thing",
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
            "shop/domain/test_thing.py",
            "shop.domain.test_thing",
            "def test_thing_exists() -> None:\n"
            "    assert True\n",
            False,
        ),
        (
            "shop/application/test_service.py",
            "shop.application.test_service",
            "def test_service_exists() -> None:\n"
            "    assert True\n",
            False,
        ),
        (
            "shop/client/client.py",
            "shop.client.client",
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
            "shop/application/service.py",
            "shop.application.service",
            "import tesser.application as ts\n"
            "import shop.client.client as client\n"
            "class AskService(ts.ApplicationService):\n"
            "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
            "        return client.AskResponse(text=request.text)\n",
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
        pure_stdlib=pure_stdlib,
    )


def test_locate_is_the_single_routing_decision() -> None:
    contexts = frozenset({"shop", "two"})
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
        ("app", True, "shell-init"),
        ("app", False, "shell-app"),
        ("app.wire", False, "shell-app"),
        ("app.__main__", False, "shell-app"),
        ("protocol", True, "protocol-init"),
        ("protocol", False, "protocol"),
        ("protocol.http", False, "protocol"),
        ("protocol.__main__", False, "protocol"),
        ("protocol.conftest", False, "conftest"),
        ("shop", True, "context-init"),
        ("shop", False, "context-init"),
        ("shop.__main__", False, "context-stray"),
        ("shop.domain", True, "role-init"),
        ("shop.domain", False, "role-file"),
        ("shop.domain.thing", False, "role"),
        ("shop.domain.__main__", False, "role"),
        ("shop.domain.sub.deep", False, "role"),
        ("shop.domain.test_thing", False, "test"),
        ("shop.domain.eval_bad", False, "eval"),
        ("shop.domain.eval_pkg", True, "eval"),
        ("shop.domain.conftest", False, "conftest"),
        ("shop.application", True, "role-init"),
        ("shop.application.service", False, "role"),
        ("shop.application.ports", True, "ports-init"),
        ("shop.application.ports", False, "ports-file"),
        ("shop.application.ports.repo", False, "ports"),
        ("shop.application.ports.sub.deep", False, "ports"),
        ("shop.application.ports.__main__", False, "ports"),
        ("shop.application.ports.test_repo", False, "ports-stray"),
        ("shop.application.ports.conftest", False, "ports-stray"),
        ("shop.application.ports.eval_repo", False, "ports-stray"),
        ("shop.adapters.gateways.__main__", False, "role"),
        ("shop.adapters.conftest", False, "conftest"),
        ("shop.adapters.conftest", True, "conftest"),
        ("shop.tests", True, "context-tests-init"),
        ("shop.tests", False, "context-tests-stray"),
        ("shop.tests.support", False, "context-tests-stray"),
        ("shop.tests.test_thing", False, "test"),
        ("shop.tests.__main__", False, "context-tests-stray"),
        ("shop.test_direct", False, "test"),
        ("shop.stray", False, "context-stray"),
        ("shop.stray_pkg.mod", False, "context-stray"),
        ("shop.conftest", False, "conftest"),
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
        and "a context role module holds classes, never functions" in f
        for f in findings
    )
    assert any("module constants are Final" in f for f in findings)
    assert any(
        "a context module holds only imports, classes, and Final constants" in f
        for f in findings
    )
    assert any(
        "imports tesser.context" in f
        and "a domain module's tesser imports are tesser.domain, "
        "tesser.errors, and tesser.serialization" in f
        for f in findings
    )


def test_a_final_constant_passes_and_a_declared_function_is_still_a_module_function() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("shop/domain2.py", "shop.domain2", "", False),
            (
                "plain/domain/thing.py",
                "plain.domain.thing",
                "from typing import Final\n"
                "import tesser.domain as ts\n"
                "LIMIT: Final[int] = 3\n"
                "def declared() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "plain/domain/test_thing.py",
                "plain.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "plain.domain.thing.declared" in f
        and "a context role module holds classes, never functions" in f
        for f in findings
    )
    assert not any("LIMIT" in f for f in findings)


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
        "a kernel, srv, app, tests, or the protocol package" in f
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
                "shop/util.py",
                "shop.util",
                "def anything() -> None:\n    return None\n",
                False,
            ),
            ("shop/__init__.py", "shop", "X = 1\n", True),
        ))).violations()
               )
    assert any(
        "shop.util" in f
        and "a context holds only domain, application, client, adapters, component, and tests modules" in f
        for f in findings
    )
    assert any("shop" in f and "a context __init__ is empty" in f for f in findings)


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
                "shop/component/component.py",
                "shop.component.component",
                "import tesser.component as ts\n"
                "import shop.application.service as application\n"
                "import shop.client.client as client\n"
                "import two.client.client as two_client\n"
                "import two.domain.thing\n"
                "class AskWiring(ts.Component):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "shop.component.component" in f and "not a context module" in f for f in findings
    )
    assert not any(
        "shop.component.component" in f and "imports shop.application.service" in f
        for f in findings
    )
    assert not any(
        "shop.component.component" in f and "imports two.client.client" in f for f in findings
    )
    assert not any(
        "shop.component.component.AskWiring" in f
        and "a kind lives only in its role module" in f
        for f in findings
    )
    assert any(
        "shop.component.component" in f
        and "imports two.domain.thing" in f
        and "a context reaches another context only through its client, and only from gateways and components" in f
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
                "shop/__main__.py",
                "shop.__main__",
                "import shop.application.service as service\nimport shop.component.component as wire\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.__main__ is not a context module; a context holds only domain, "
        "application, client, adapters, component, and tests modules" in f
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
                "import shop.client.client\n"
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
                "def fine() -> None:\n"
                "    return None\n"
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
    assert any(
        "protocol.box.fine" in f
        and "a protocol module holds classes, never functions" in f
        for f in findings
    )
    assert not any("protocol.box belongs to no governed package" in f for f in findings)
    assert any(
        "protocol.box imports shop.client.client; a protocol module is context-generic and imports no context" in f
        for f in findings
    )
    assert any(
        "protocol.box imports srv.host; a protocol module never imports srv or app" in f
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
        and "a protocol module holds classes, never functions" in f
        for f in findings
    )
    assert (
        len(
            [
                f
                for f in findings
                if "protocol.box" in f
                and "declares a module constant without Final; protocol constants are Final" in f
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
        "declared classes, and Final constants" in f
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
        "protocol.form imports names from tesser.srv; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
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
            (
                "protocol/test_box.py",
                "protocol.test_box",
                "def test_box_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
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
    assert set(checks.KIND_ROLE) == blocks - checks.SRV_KINDS - checks.APP_KINDS
    assert not (checks.APP_KINDS & set(checks.KIND_ROLE))


def test_mapper_shape_rules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/sloppy.py",
                "shop.application.sloppy",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest\n"
                "class Sloppy(ts.Mapper):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self._text = text\n"
                "        self._tag = 'fixed'\n"
                "    def compute(self) -> str:\n"
                "        return self._text\n",
                False,
            ),
            (
                "shop/application/nested.py",
                "shop.application.nested",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest\n"
                "class MapToOther(ts.Mapper):\n"
                "    def __init__(self, request: AskRequest) -> None:\n"
                "        self._request = request\n"
                "class MapToThing(ts.Mapper):\n"
                "    def __init__(self, request: AskRequest) -> None:\n"
                "        self._other = MapToOther(request)\n"
                "    @property\n"
                "    def other(self) -> MapToOther:\n"
                "        return self._other\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.sloppy.Sloppy" in f
        and "does not start with MapTo" in f
        and "a mapper is named for what it maps to, because its parameters "
        "already say what it maps from" in f
        for f in findings
    )
    assert any(
        "shop.application.sloppy.Sloppy parameter 'text' is a primitive" in f
        and "a mapper takes whole objects, never a field already pulled off one" in f
        for f in findings
    )
    assert any(
        "shop.application.sloppy.Sloppy.compute is a method" in f
        and "a mapper holds only __init__ and the accessors it exposes" in f
        for f in findings
    )
    assert any(
        "shop.application.sloppy.Sloppy carries the literal 'fixed'" in f
        and "a mapper originates nothing — every value it exposes comes from "
        "what it was given" in f
        for f in findings
    )
    assert any(
        "shop.application.nested.MapToThing.other returns a mapper" in f
        and "a nested mapper accessor ends in _mapper, so the reader knows to "
        "keep dotting" in f
        for f in findings
    )


def test_an_index_and_an_error_message_are_not_originated_data() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/reading.py",
                "shop.application.reading",
                "import tesser.application as ts\n"
                "import shop.client.client as client\n"
                "from tesser.errors import not_found\n"
                "class MapToFirst(ts.Mapper):\n"
                "    def __init__(self, answer: client.AskResponse) -> None:\n"
                "        if not answer.rows:\n"
                "            raise not_found('row_missing', 'no row in the answer')\n"
                "        self._answer = answer\n"
                "        self._first = answer.rows[0]\n",
                False,
            ),
        ))).violations()
               )
    assert not any("originates nothing" in f for f in findings), findings


def test_a_conformant_mapper_passes_every_shape_rule() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/good.py",
                "shop.application.good",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest\n"
                "class MapToInner(ts.Mapper):\n"
                "    def __init__(self, request: AskRequest) -> None:\n"
                "        self._request = request\n"
                "        self._text = request.text\n"
                "    @property\n"
                "    def text(self) -> str:\n"
                "        return self._text\n"
                "class MapToOuter(ts.Mapper):\n"
                "    def __init__(self, request: AskRequest) -> None:\n"
                "        self._request = request\n"
                "        self._inner_mapper = MapToInner(request)\n"
                "    @property\n"
                "    def inner_mapper(self) -> MapToInner:\n"
                "        return self._inner_mapper\n",
                False,
            ),
        ))).violations()
               )
    assert not any("a mapper" in f for f in findings), findings


def test_a_mapper_lives_only_in_the_application_role() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/mapping.py",
                "shop.application.mapping",
                "import tesser.application as ts\n"
                "class MapToThing(ts.Mapper):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/domain/mapping.py",
                "shop.domain.mapping",
                "import tesser.application as ts\n"
                "class MapToOther(ts.Mapper):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "shop.application.mapping.MapToThing" in f and "declares no ts.* base" in f
        for f in findings
    )
    assert not any(
        "shop.application.mapping.MapToThing" in f
        and "a kind lives only in its role module" in f
        for f in findings
    )
    assert any(
        "shop.domain.mapping.MapToOther" in f
        and "is a mapper, whose home is application.py" in f
        and "a kind lives only in its role module" in f
        for f in findings
    )


def test_every_kind_row_names_a_real_tesser_export() -> None:
    root = pathlib.Path(__file__).resolve().parents[3] / "tesser-py"
    rows = list(checks.TESSER_BASE_BLOCKS) + list(checks.TESSER_DECORATORS)
    for package, name in rows:
        exports = (root / package.replace(".", "/") / "__init__.py").read_text()
        assert f" {name} as {name}" in exports


def test_primitive_parameter_and_return_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/bad.py",
                "shop.bad",
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
                "shop/bad.py",
                "shop.bad",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest, AskResponse\n"
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
                "shop/badroots.py",
                "shop.badroots",
                "import tesser.domain as ts\n"
                "from shop.domain.thing import ThingSpec\n"
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


def test_computing_in_an_argument_and_assembling_from_two_readers_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/client/client.py",
                "shop.client.client",
                "import tesser.context as ts\n"
                "class AskRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class AskResponse(ts.Response):\n"
                "    def __init__(self, text: str, tag: str) -> None:\n"
                "        self.text = text\n"
                "        self.tag = tag\n",
                False,
            ),
            (
                "shop/application/service.py",
                "shop.application.service",
                "import tesser.application as ts\n"
                "import shop.client.client as client\n"
                "class NestingService(ts.ApplicationService):\n"
                "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
                "        return client.AskResponse(text=str(request.text), tag='t')\n"
                "    def spread(self, request: client.AskRequest) -> client.AskResponse:\n"
                "        first = self._one(request)\n"
                "        second = self._two(request)\n"
                "        return client.AskResponse(text=first.text, tag=second.tag)\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "NestingService.ask computes in an argument" in f
        and "a service method names what it computes in a local, and passes a name, "
        "a reader, or a declared kind" in f
        for f in findings
    )
    assert any(
        "NestingService.spread assembles from 2 readers" in f
        and "a declared kind is assembled from the accessors of one mapper" in f
        for f in findings
    )


def test_a_mapper_that_constructs_its_target_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/client/client.py",
                "shop.client.client",
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
                "shop/application/eager.py",
                "shop.application.eager",
                "import tesser.application as ts\n"
                "import shop.client.client as client\n"
                "class MapToAskResponse(ts.Mapper):\n"
                "    def __init__(self, request: client.AskRequest) -> None:\n"
                "        self._request = request\n"
                "        self._response = client.AskResponse(text=request.text)\n"
                "    @property\n"
                "    def response(self) -> client.AskResponse:\n"
                "        return self._response\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.eager.MapToAskResponse constructs what it maps to" in f
        and "a mapper exposes the parts and the caller assembles them, so every field "
        "is named where it is read" in f
        for f in findings
    )


def test_a_raw_request_value_reaching_a_port_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/provenance.py",
                "shop.provenance",
                "import tesser.application as ts\n"
                "import shop.domain.thing as thing\n"
                "from shop.client.client import AskRequest, AskResponse\n"
                "from shop.application.ports.thing_repository import FindThingRequest\n"
                "class ProvenanceService(ts.ApplicationService):\n"
                "    def raw(self, request: AskRequest) -> AskResponse:\n"
                "        found = self._repo.find(FindThingRequest(name=request.name))\n"
                "        return AskResponse(text=found.name)\n"
                "    def through_the_domain(self, request: AskRequest) -> AskResponse:\n"
                "        name = thing.Name(request.name)\n"
                "        found = self._repo.find(FindThingRequest(name=str(name)))\n"
                "        return AskResponse(text=found.name)\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "ProvenanceService.raw sends name from its request straight to a port" in f
        and "a value crossing into a port has passed through a domain type" in f
        for f in findings
    )
    assert not any(
        "ProvenanceService.through_the_domain sends" in f for f in findings
    ), findings


def test_a_straight_accessor_local_is_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/naming.py",
                "shop.naming",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest, AskResponse\n"
                "class NamingService(ts.ApplicationService):\n"
                "    def echo(self, request: AskRequest) -> AskResponse:\n"
                "        text = request.text\n"
                "        return AskResponse(text=text)\n"
                "    def computes(self, request: AskRequest) -> AskResponse:\n"
                "        text = str(request.text)\n"
                "        return AskResponse(text=text)\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "NamingService.echo names a straight accessor" in f
        and "a service method names what it computes, and reads an accessor "
        "where it is used" in f
        for f in findings
    )
    assert not any("NamingService.computes names a straight accessor" in f for f in findings)


def test_service_body_rules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/busy.py",
                "shop.busy",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest, AskResponse\n"
                "class BusyService(ts.ApplicationService):\n"
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
                "shop/helped.py",
                "shop.helped",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest, AskResponse\n"
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
                "shop/chained.py",
                "shop.chained",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest, AskResponse\n"
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
                "shop/derived.py",
                "shop.derived",
                "from shop.application.service import AskService\n"
                "from shop.client.client import AskRequest\n"
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
                "shop/extra.py",
                "shop.extra",
                "import tesser.application as ts\n"
                "from shop.client.client import AskRequest, AskResponse\n"
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
                "shop/extra2.py",
                "shop.extra2",
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
                "shop/extra3.py",
                "shop.extra3",
                "from typing import Protocol\n"
                "import tesser.adapters as ta\n"
                "import tesser.application as tap\n"
                "from shop.domain.thing import Thing\n"
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
                "shop/extra4.py",
                "shop.extra4",
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
                "        return None\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "class TagSpec(ts.Spec):\n"
                "    def __init__(self, value: str) -> None:\n"
                "        self.value = value\n"
                "class Wrap(ts.ValueObject):\n"
                "    def __init__(self, tag: Tag) -> None:\n"
                "        object.__setattr__(self, '_tag', tag)\n"
                "class FromSpec(ts.ValueObject):\n"
                "    def __init__(self, spec: TagSpec) -> None:\n"
                "        object.__setattr__(self, '_value', spec.value)\n"
                "class CarrySpec(ts.Spec):\n"
                "    def __init__(self, tag: Tag) -> None:\n"
                "        self.tag = tag\n"
                "class NoInitVO(ts.ValueObject):\n"
                "    _value: str\n"
                "class VarargVO(ts.ValueObject):\n"
                "    def __init__(self, *args: str, **kwargs: str) -> None:\n"
                "        object.__setattr__(self, '_values', args)\n"
                "class NoInitSpec(ts.Spec):\n"
                "    name: str\n"
                "class VarargSpec(ts.Spec):\n"
                "    def __init__(self, **fields: str) -> None:\n"
                "        self.fields = fields\n"
                "class SmuggleSpec(ts.Spec):\n"
                "    amount: Tag\n"
                "    def __init__(self, name: str) -> None:\n"
                "        self.name = name\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "Money.__init__" in f
        and "a value object constructs from primitives and specs, never value objects" in f
        for f in findings
    )
    assert any(
        "BagSpec.__init__" in f
        and "a spec field is a primitive or a child spec, never a value object" in f
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
    assert any(
        "Wrap.__init__" in f and "parameter 'tag' is not allowed" in f
        and "a value object constructs from primitives and specs, never value objects" in f
        for f in findings
    )
    assert not any("FromSpec.__init__ parameter" in f for f in findings)
    assert any(
        "CarrySpec.__init__" in f and "parameter 'tag' is not allowed" in f
        and "a spec field is a primitive or a child spec, never a value object" in f
        for f in findings
    )
    assert any(
        "NoInitVO defines no __init__" in f
        and "a value object constructs in its own __init__" in f
        for f in findings
    )
    assert any(
        "VarargVO.__init__ uses *args/**kwargs" in f
        and "a value object declares its construction data as named parameters" in f
        for f in findings
    )
    assert any(
        "NoInitSpec defines no __init__" in f
        and "a spec defines the __init__ that carries its fields" in f
        for f in findings
    )
    assert any(
        "VarargSpec.__init__ uses *args/**kwargs" in f
        and "a spec declares its fields as named __init__ parameters, where the field rules can read them" in f
        for f in findings
    )
    assert any(
        "SmuggleSpec carries a class-level statement" in f
        and "a spec declares its fields as __init__ parameters, where the field rules can read them" in f
        for f in findings
    )


def test_construction_containers_discriminate_specs_from_value_objects() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/carton.py",
                "shop.domain.carton",
                "import tesser.domain as ts\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, value: str) -> None:\n"
                "        object.__setattr__(self, '_value', value)\n"
                "class TagSpec(ts.Spec):\n"
                "    def __init__(self, value: str) -> None:\n"
                "        self.value = value\n"
                "class WrapsMany(ts.ValueObject):\n"
                "    def __init__(self, tags: tuple[Tag, ...]) -> None:\n"
                "        object.__setattr__(self, '_tags', tags)\n"
                "class WrapsMaybe(ts.ValueObject):\n"
                "    def __init__(self, tag: Tag | None) -> None:\n"
                "        object.__setattr__(self, '_tag', tag)\n"
                "class FromSpecs(ts.ValueObject):\n"
                "    def __init__(self, specs: tuple[TagSpec, ...]) -> None:\n"
                "        object.__setattr__(self, '_values', tuple(s.value for s in specs))\n"
                "class FromMaybeSpec(ts.ValueObject):\n"
                "    def __init__(self, spec: TagSpec | None) -> None:\n"
                "        object.__setattr__(self, '_value', spec.value if spec is not None else '')\n"
                "class CartonSpec(ts.Spec):\n"
                "    def __init__(self, tags: tuple[Tag, ...], tag: Tag | None, children: tuple[TagSpec, ...], child: TagSpec | None) -> None:\n"
                "        self.tags = tags\n"
                "        self.tag = tag\n"
                "        self.children = children\n"
                "        self.child = child\n"
                "class ForwardSpec(ts.Spec):\n"
                "    def __init__(self, child: 'TagSpec | None', kids: tuple['ForwardSpec', ...], bad: 'Tag') -> None:\n"
                "        self.child = child\n"
                "        self.kids = kids\n"
                "        self.bad = bad\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "WrapsMany.__init__" in f and "parameter 'tags' is not allowed" in f
        and "a value object constructs from primitives and specs, never value objects" in f
        for f in findings
    )
    assert any(
        "WrapsMaybe.__init__" in f and "parameter 'tag' is not allowed" in f
        for f in findings
    )
    assert not any("FromSpecs.__init__ parameter" in f for f in findings)
    assert not any("FromMaybeSpec.__init__ parameter" in f for f in findings)
    assert any(
        "CartonSpec.__init__" in f and "parameter 'tags' is not allowed" in f
        and "a spec field is a primitive or a child spec, never a value object" in f
        for f in findings
    )
    assert any(
        "CartonSpec.__init__" in f and "parameter 'tag' is not allowed" in f
        for f in findings
    )
    assert not any("parameter 'children'" in f for f in findings)
    assert not any("parameter 'child'" in f for f in findings)
    assert not any("parameter 'kids'" in f for f in findings)
    assert any(
        "ForwardSpec.__init__" in f and "parameter 'bad' is not allowed" in f
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
                "shop/domain/opt.py",
                "shop.domain.opt",
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
        "a spec field is a primitive or a child spec, never a value object" in f
        for f in findings
    )
    assert any("parameter 'mix' is not allowed" in f for f in findings)


def test_bytes_is_construction_primitive() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/digest.py",
                "shop.domain.digest",
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
                "shop/client/async_client.py",
                "shop.client.async_client",
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
                "shop/adapters/gateways/async_repo.py",
                "shop.adapters.gateways.async_repo",
                "from __future__ import annotations\n"
                "import tesser.adapters as ts\n"
                "import shop.domain.thing as thing\n"
                "class Loose(ts.Repository):\n"
                "    async def save(self, entity: thing.Thing) -> None: ...\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.client.async_client.Loose.ask" in f
        and "a client method takes exactly one" in f
        for f in findings
    ), f"an async client method escaped the client shape rule: {findings}"
    assert any(
        "shop.adapters.gateways.async_repo.Loose.save carries an aggregate in its signature"
        in f
        for f in findings
    ), f"an async adapter method escaped the record rule: {findings}"


def test_an_adapters_module_holds_one_kind() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/adapters/gateways.py",
                "shop.adapters.gateways",
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
        "shop.adapters.gateways mixes adapter kinds" in f
        and "an adapters module holds one adapter kind" in f
        for f in findings
    )


def test_a_dotted_module_base_resolves() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/test_doubles.py",
                "shop.test_doubles",
                "import tesser.testing as th\n"
                "import shop.application.service\n"
                "@th.fake\n"
                "class FakePort(shop.application.service.AskService):\n"
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
        "FakePort" in f and "a fake implements the contract it doubles" in f
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
                "import shop.client.client as shop_client\n"
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
                "import shop.domain.thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "two.domain.thing" in f
        and "the same-context matrix is a role to itself, application to domain and client, adapters to application/ports, component to application, adapters, and client" in f
        for f in findings
    )
    assert any(
        "two.application.service" in f
        and "a context reaches another context only through its client, and only from gateways and components" in f
        for f in findings
    )
    assert not any("two.adapters.gateways" in f and "imports shop.client.client" in f for f in findings)


def test_srv_and_app_import_rows() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/adapters/gateways.py",
                "shop.adapters.gateways",
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
                "import shop.application.service\n"
                "import shop.adapters.gateways as app_adapters\n"
                "import two.adapters.gateways\n"
                "import app.wire\n",
                False,
            ),
            (
                "app/wire.py",
                "app.wire",
                "import shop.domain.thing\n"
                "import shop.component.component as wiring\n"
                "import shop.client.client as shop_client\n"
                "import srv.http\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.http" in f and "imports shop.application.service" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert any(
        "srv.http" in f and "imports two.adapters.gateways" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.http" in f and "imports shop.adapters.gateways" in f for f in findings)
    assert not any("srv.http" in f and "imports app.wire" in f for f in findings)
    assert any(
        "app.wire" in f and "imports shop.domain.thing" in f
        and "an app builds from components, clients, and adapters, never domain or application" in f
        for f in findings
    )
    assert not any("app.wire" in f and "imports shop.component.component" in f for f in findings)
    assert not any("app.wire" in f and "imports shop.client.client" in f for f in findings)
    assert any(
        "app.wire" in f and "imports srv.http" in f
        and "the composition root never imports a host" in f
        for f in findings
    )


def test_only_a_handler_imports_its_own_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/adapters/gateways.py",
                "shop.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import shop.client.client as shop_client\n"
                "class HttpHandler(ts.Handler):\n"
                "    def ask(self, body: str) -> str:\n"
                "        return shop_client.AskRequest(text=body).text\n",
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
    assert not any("shop.adapters.gateways" in f and "imports shop.client.client" in f for f in findings)
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
                "shop/adapters/gateways.py",
                "shop.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import two.client.client\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.adapters.gateways" in f and "imports two.client.client" in f
        and "a context reaches another context only through its client, and only from gateways and components" in f
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
        "fromform.domain.thing imports names from tesser.domain; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
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
        "pkg.domain imports names from pkg.domain.vo; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    )
    assert len([f for f in findings if "TB053" in f]) == 1, findings


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
        "mod.domain imports names from mod.domain.vo; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in tuple(
                     f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                     for v in checks.Codebase(_spec(sources=(vo, class_form, client, client_init))).violations()
                 )
    )


def test_srv_and_app_statement_totality() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/box.py",
                "srv.box",
                "import tesser.srv as ts\n"
                "import tesser.domain as td\n"
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
                "app/wire.py",
                "app.wire",
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
        "are tesser.srv, and tesser.errors" in f
        for f in findings
    )
    assert any(
        "srv.box.stray" in f
        and "a srv module holds classes, never functions" in f
        for f in findings
    )
    assert any(
        "srv.box.fine" in f and "a srv module holds classes, never functions" in f
        for f in findings
    )
    assert any(
        "srv.box.Box" in f and "declares no ts.* base; a srv class declares its block" in f
        for f in findings
    )
    assert not any("srv.box.Server" in f for f in findings)
    assert any(
        "srv.box" in f and "declares a module constant without Final; srv constants are Final" in f
        for f in findings
    )
    assert any(
        "srv.box" in f and "has a loose module-level statement; a srv module holds only imports, "
        "declared classes, and Final constants" in f
        for f in findings
    )
    assert any(
        "app.wire never imports tesser.app; "
        "an app module imports tesser.app exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "app.wire.build" in f
        and "an app function declares itself with @ts.load" in f
        for f in findings
    )
    assert any(
        "app.wire.App" in f
            and "declares no ts.* base; every app class declares its block" in f
        for f in findings
    )
    assert any(
        "app.wire" in f
        and "declares a module constant without Final; app constants are Final" in f
        for f in findings
    )
    assert any(
        "app.wire" in f
        and "has a loose module-level statement; an app module holds only imports, "
        "classes, declared functions, and Final constants" in f
        for f in findings
    )


def test_a_srv_entry_point_is_ts_main_and_nothing_else() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/good.py",
                "srv.good",
                "import tesser.srv as ts\n"
                "class Run(ts.Host):\n"
                "    def run(self, argv: list[str]) -> int:\n"
                "        return 0\n"
                "if __name__ == '__main__':\n"
                "    ts.main(Run().run)\n",
                False,
            ),
            (
                "srv/test_good.py",
                "srv.test_good",
                "import srv.good as good\n"
                "def test_run() -> None:\n"
                "    assert good.Run().run([]) == 0\n",
                False,
            ),
            (
                "srv/busy.py",
                "srv.busy",
                "import sys\n"
                "import tesser.srv as ts\n"
                "class Run(ts.Host):\n"
                "    def run(self, argv: list[str]) -> int:\n"
                "        return 0\n"
                "if __name__ == '__main__':\n"
                "    print('starting')\n"
                "    ts.main(Run().run)\n",
                False,
            ),
            (
                "srv/legacy.py",
                "srv.legacy",
                "import sys\n"
                "import tesser.srv as ts\n"
                "class Run(ts.Host):\n"
                "    def run(self, argv: list[str]) -> int:\n"
                "        return 0\n"
                "if __name__ == '__main__':\n"
                "    raise SystemExit(Run().run(sys.argv[1:]))\n",
                False,
            ),
            (
                "srv/branching.py",
                "srv.branching",
                "import tesser.srv as ts\n"
                "class Run(ts.Host):\n"
                "    def run(self, argv: list[str]) -> int:\n"
                "        return 0\n"
                "if __name__ == '__main__':\n"
                "    ts.main(Run().run)\n"
                "else:\n"
                "    ts.main(Run().run)\n",
                False,
            ),
            (
                "app/boot.py",
                "app.boot",
                "import tesser.app as ts\n"
                "if __name__ == '__main__':\n"
                "    ts.main(print)\n",
                False,
            ),
        ))).violations()
               )
    assert not any("srv.good" in f for f in findings)
    for module in ("srv.busy", "srv.legacy", "srv.branching"):
        assert any(
            f"{module} has a __main__ guard holding more than ts.main(run); "
            "a srv module's entry point is ts.main(run) and nothing else" in f
            for f in findings
        ), module
    assert any(
        "app.boot has a loose module-level statement; an app module holds only imports, "
        "classes, declared functions, and Final constants" in f
        for f in findings
    )


def test_sibling_reference_scoping_and_spoof_resistance() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "plain/domain/y.py",
                "plain.domain.y",
                "import tesser.domain as ts\n"
                "class Scoped(ts.ValueObject):\n"
                "    def outer(self) -> int:\n"
                "        class Inner:\n"
                "            def go(self) -> int:\n"
                "                return self.pick()\n"
                "            def pick(self) -> int:\n"
                "                return 1\n"
                "        return Inner().go()\n"
                "    def pick(self) -> int:\n"
                "        return 2\n"
                "    def taken(self) -> object:\n"
                "        return [self.pick() for self in []]\n"
                "    @staticmethod\n"
                "    def convert(collaborator: object) -> object:\n"
                "        cls = collaborator\n"
                "        return cls.pick()\n"
                "    def stash(self) -> None:\n"
                "        self.note = 5\n"
                "    def note(self) -> int:\n"
                "        return 3\n"
                "class Renamed(ts.ValueObject):\n"
                "    def run(this) -> int:\n"
                "        return this.helper()\n"
                "    def helper(this) -> int:\n"
                "        return 1\n"
                "class Spoof(ts.ValueObject):\n"
                "    def caller(self) -> int:\n"
                "        return self.marked()\n"
                "    def marked(self) -> int:\n"
                "        _ = self.marked\n"
                "        return 0\n"
                "class Closure(ts.ValueObject):\n"
                "    def build(self) -> object:\n"
                "        def call() -> int:\n"
                "            return self.helper()\n"
                "        return call\n"
                "    def helper(self) -> int:\n"
                "        return 1\n"
                "class Guarded(ts.ValueObject):\n"
                "    if True:\n"
                "        def helper(self) -> int:\n"
                "            return 1\n"
                "    def run(self) -> int:\n"
                "        return self.helper()\n"
                "class Dunder(ts.ValueObject):\n"
                "    def __len__(self) -> int:\n"
                "        return 1\n"
                "    def size(self) -> int:\n"
                "        return self.__len__()\n"
                "class Classy(ts.ValueObject):\n"
                "    @classmethod\n"
                "    def build(cls) -> int:\n"
                "        return cls.seeded()\n"
                "    @classmethod\n"
                "    def seeded(cls) -> int:\n"
                "        return 1\n",
                False,
            ),
        ))).violations()
               )
    sibling = [f for f in findings if "reaches sibling" in f]
    assert not any("Scoped.outer" in f for f in sibling)
    assert any(
        "plain.domain.y.Inner.go reaches sibling pick; a method is for outsiders "
        "— a class reaches into itself only for direct recursion" in f
        for f in sibling
    )
    assert not any("Scoped.taken" in f for f in sibling)
    assert not any("Scoped.convert" in f for f in sibling)
    assert not any("Scoped.stash" in f for f in sibling)
    assert any("Renamed.run reaches sibling helper" in f for f in sibling)
    assert any("Spoof.caller reaches sibling marked" in f for f in sibling)
    assert not any("Spoof.marked reaches" in f for f in sibling)
    assert any("Closure.build reaches sibling helper" in f for f in sibling)
    assert any("Guarded.run reaches sibling helper" in f for f in sibling)
    assert not any("Dunder.size" in f for f in sibling)
    assert any("Classy.build reaches sibling seeded" in f for f in sibling)


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
                "import pathlib\n"
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
                "form/component/component.py",
                "form.component.component",
                "import tesser.component as ts\n"
                "import form.application.service\n"
                "class PingWiring(ts.Component):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "form.application.service imports names from form.client.client; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    )
    assert any(
        "form.component.component imports form.application.service without an alias; "
        "a context module is imported as an aliased module — the analyzer "
        "resolves a name as attribute over alias" in f
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
                "rel/component/component.py",
                "rel.component.component",
                "import tesser.component as ts\n"
                "from ..client.client import RelRequest\n"
                "class RelWiring(ts.Component):\n"
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
        "rel.domain imports names from rel.domain.money; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    )
    assert any(
        "rel.component.component imports names from rel.client.client; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
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


def test_srv_and_app_tesser_form_modes() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/dup.py",
                "srv.dup",
                "import tesser.srv as ts\n"
                "import tesser.srv as ts\n"
                "def go() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "srv/test_dup.py",
                "srv.test_dup",
                "def test_dup_exists() -> None:\n"
                "    assert True\n",
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
                "srv/test_alias.py",
                "srv.test_alias",
                "def test_alias_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "app/fromform.py",
                "app.fromform",
                "from tesser.app import load\n"
                "@load\n"
                "def go() -> None:\n"
                "    return None\n",
                False,
            ),
            (
                "app/test_fromform.py",
                "shop.test_fromform",
                "def test_fromform_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "app/wrongpkg.py",
                "app.wrongpkg",
                "import tesser.context as ts\n"
                "import tesser.domain as td\n",
                False,
            ),
            (
                "app/test_wrongpkg.py",
                "shop.test_wrongpkg",
                "def test_wrongpkg_exists() -> None:\n"
                "    assert True\n",
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
                "srv/test_consts.py",
                "srv.test_consts",
                "def test_consts_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "srv/annconst.py",
                "srv.annconst",
                "LIMIT: int = 3\n",
                False,
            ),
            (
                "srv/test_annconst.py",
                "srv.test_annconst",
                "def test_annconst_exists() -> None:\n"
                "    assert True\n",
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
            (
                "srv/test_tfinal.py",
                "srv.test_tfinal",
                "def test_tfinal_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("srv/__init__.py", "srv", "X = 1\n", True),
            ("app/__init__.py", "app", "", True),
            (
                "konst/domain/thing.py",
                "konst.domain.thing",
                "from typing import Final\n"
                "LIMIT: Final[int] = 3\n",
                False,
            ),
            (
                "konst/domain/test_thing.py",
                "konst.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
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
        "app.fromform imports names from tesser.app; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    )
    assert any(
        "app.wrongpkg imports tesser.domain; "
        "an app module's tesser imports are tesser.app, "
        "and tesser.errors" in f
        for f in findings
    )
    assert any(
        "srv.consts never imports tesser.srv; "
        "a srv module imports tesser.srv exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "srv.annconst declares a module constant without Final; "
        "srv constants are Final" in f
        for f in findings
    )
    assert not any("srv.tfinal" in f for f in findings)
    assert any(
        "konst.domain.thing never imports tesser.domain; "
        "a role module imports its tesser package exactly once, as ts" in f
        for f in findings
    )
    assert any(
        "srv __init__ declares code; a srv or app __init__ is empty" in f
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
                "shop/adapters/gateways.py",
                "shop.adapters.gateways",
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
        "shop.adapters.gateways.Sneaky" in f
        and "is a host; a host lives in srv and a protocol kind in a protocol module, never a context" in f
        for f in findings
    )
    assert any(
        "shop.adapters.gateways.WireAsk" in f
        and "is a protocol request record; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "shop.adapters.gateways.WireReply" in f
        and "is a protocol response record; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "shop.adapters.gateways.WireDoor" in f
        and "is a protocol port; a host lives in srv and a protocol kind in a protocol module, "
        "never a context" in f
        for f in findings
    )
    assert any(
        "shop.adapters.gateways.WireLabel" in f
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
                "shop/test_forms.py",
                "shop.test_forms",
                "from shop.domain.thing import Thing\n"
                "def test_thing() -> None:\n"
                "    assert Thing\n",
                False,
            ),
            (
                "shop/adapters/gateways.py",
                "shop.adapters.gateways",
                "import tesser.adapters as ts\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            (
                "srv/http.py",
                "srv.http",
                "from shop.adapters.gateways import HttpHandler\n",
                False,
            ),
            (
                "skipctx/domain/thing.py",
                "skipctx.domain.thing",
                "import tesser.domain as ts\n"
                "import shop.client.client\n"
                "class SkipSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.test_forms imports names from shop.domain.thing; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    )
    assert any(
        "srv.http imports names from shop.adapters.gateways; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    )
    assert any(
        "skipctx.domain.thing imports shop.client.client; a context reaches another context "
        "only through its client, and only from gateways and components" in f
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
                "import shop.domain\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.host imports shop.domain" in f
        and "a host reaches a context only through its handlers" in f
        for f in findings
    )
    assert not any("srv.host" in f and "attribute over alias" in f for f in findings)


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
                "app/wire.py",
                "app.wire",
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
        "app.wire imports tests.test_ok; "
        "production code never imports the tests package" in f
        for f in findings
    )
    assert any(
        "app.wire imports protocol.http; "
        "an app composes the application and never imports protocol" in f
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
                "shop/adapters/handlers.py",
                "shop.adapters.handlers",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n"
                "import srv.http as host\n"
                "class HttpHandler(ts.Handler):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/component/component.py",
                "shop.component.component",
                "import tesser.component as ts\n"
                "import protocol.http as http\n",
                False,
            ),
            (
                "shop/adapters/gateways.py",
                "shop.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n"
                "class PeerGateway(ts.Gateway):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/adapters/handlers_support.py",
                "shop.adapters.handlers_support",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n",
                False,
            ),
            ("shop/adapters/repositories/__init__.py", "shop.adapters.repositories", "", True),
            (
                "shop/adapters/repositories/smuggle.py",
                "shop.adapters.repositories.smuggle",
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
        "shop.adapters.handlers imports srv.http; "
        "of the app shell a context imports only protocol, and only from its handlers" in f
        for f in findings
    )
    assert not any("shop.adapters.handlers imports protocol.http" in f for f in findings)
    assert any(f"shop.component.component imports protocol.http; {clause}" in f for f in findings)
    assert any(
        f"shop.adapters.gateways imports protocol.http; {clause}" in f for f in findings
    ), f"a gateway imported protocol without a finding: {findings}"
    assert any(
        f"shop.adapters.handlers_support imports protocol.http; {clause}" in f
        for f in findings
    ), f"a handlers-adjacent name bought the grant without the placement: {findings}"
    assert any(
        f"shop.adapters.repositories.smuggle imports protocol.http; {clause}" in f
        for f in findings
    ), f"a Handler class declared outside handlers/ bought the grant: {findings}"


def test_a_classless_module_inside_handlers_may_speak_protocol() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("protocol/http.py", "protocol.http", "import tesser.srv as ts\n", False),
            ("shop/adapters/handlers/__init__.py", "shop.adapters.handlers", "", True),
            (
                "shop/adapters/handlers/usage.py",
                "shop.adapters.handlers.usage",
                "import tesser.adapters as ts\n"
                "import protocol.http as http\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "shop.adapters.handlers.usage imports protocol.http" in f for f in findings
    ), f"a helper module inside handlers/ was denied protocol: {findings}"


def test_a_shell_name_missing_from_the_tree_is_not_the_shell() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/test_thing.py",
                "shop.domain.test_thing",
                "import protocol.thirdparty\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "shop/component/component.py",
                "shop.component.component",
                "import tesser.context as ts\nimport bootstrap\n",
                False,
            ),
        ))).violations()
               )
    assert not any("shop.domain.test_thing imports protocol.thirdparty" in f for f in findings)
    assert not any("shop.component.component imports bootstrap" in f for f in findings)


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
                "import shop.domain.thing\nimport enum\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "helpers belongs to no governed package; every module belongs to a "
        "context, a kernel, srv, app, tests, or the protocol package" in f
        for f in findings
    )


def test_a_root_conftest_is_a_leaf() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "conftest.py",
                "conftest",
                "import os\nimport sys\nimport shop.domain.thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "conftest imports shop.domain.thing; "
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


def test_a_norm_module_is_imported_as_a_module_where_its_placement_allows() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "fine/domain/money.py",
                "fine.domain.money",
                "import tesser.domain as ts\n"
                "import tesser.serialization as serialization\n"
                "class MoneySpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = serialization.canonical_str(code)\n",
                False,
            ),
            (
                "fine/domain/test_money.py",
                "fine.domain.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "member/domain/money.py",
                "member.domain.money",
                "import tesser.domain as ts\n"
                "from tesser.serialization import canonical_str\n"
                "class MemberSpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = canonical_str(code)\n",
                False,
            ),
            (
                "member/domain/test_money.py",
                "member.domain.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
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
                "whole/domain/test_money.py",
                "whole.domain.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "appside/application/service.py",
                "appside.application.service",
                "import tesser.application as ts\n"
                "import tesser.serialization as serialization\n"
                "class SideService(ts.ApplicationService):\n"
                "    def ask(self, code: str) -> str:\n"
                "        return serialization.canonical_str(code)\n",
                False,
            ),
            (
                "appside/application/test_service.py",
                "appside.application.test_service",
                "def test_service_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "only/domain/money.py",
                "only.domain.money",
                "import tesser.serialization as serialization\n"
                "class OnlyMoney:\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = serialization.canonical_str(code)\n",
                False,
            ),
            (
                "only/domain/test_money.py",
                "only.domain.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert not any("fine.domain.money" in f for f in findings)
    assert any(
        "whole.domain.money imports tesser.serialization without an alias; a norm module "
        "is imported as an aliased module — a bare import binds the whole tesser package, "
        "and the ts alias belongs to the placement's own package" in f
        for f in findings
    )
    assert any(
        "member.domain.money imports names from tesser.serialization; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
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


def test_wiring_bootstrap_and_srv_may_import_tesser_errors_as_a_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/component/component.py",
                "shop.component.component",
                "import tesser.component as ts\n"
                "import tesser.errors as errors\n"
                "class Wiring(ts.Component):\n"
                "    def close(self) -> None:\n"
                "        return None\n",
                False,
            ),
            (
                "shop/component/test_component.py",
                "shop.component.test_component",
                "def test_wire_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "app/wire.py",
                "app.wire",
                "import tesser.app as ts\n"
                "import tesser.errors as errors\n",
                False,
            ),
            (
                "app/test_component.py",
                "app.test_component",
                "def test_wire_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "srv/run.py",
                "srv.run",
                "import tesser.srv as ts\n"
                "import tesser.errors as errors\n",
                False,
            ),
            (
                "srv/test_run.py",
                "srv.test_run",
                "def test_run_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "member/component/component.py",
                "member.component.component",
                "import tesser.component as ts\n"
                "from tesser.errors import invalid\n"
                "class Wiring(ts.Component):\n"
                "    def close(self) -> None:\n"
                "        return None\n",
                False,
            ),
            (
                "member/component/test_component.py",
                "member.component.test_component",
                "def test_wire_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "astray/component/component.py",
                "astray.component.component",
                "import tesser.component as ts\n"
                "import tesser.domain\n"
                "class Wiring(ts.Component):\n"
                "    pass\n",
                False,
            ),
            (
                "astray/component/test_component.py",
                "astray.component.test_component",
                "def test_wire_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert not any("shop.component.component" in f for f in findings)
    assert not any("app.wire" in f and "tesser.errors" in f for f in findings)
    assert not any("srv.run" in f and "tesser.errors" in f for f in findings)
    assert any(
        "member.component.component imports names from tesser.errors; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    )
    assert any(
        "astray.component.component imports tesser.domain; "
        "a component module's tesser imports are tesser.component, "
        "and tesser.errors" in f
        for f in findings
    )


def test_any_role_but_client_may_import_tesser_errors_as_a_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/money.py",
                "shop.domain.money",
                "import tesser.domain as ts\n"
                "import tesser.errors as errors\n"
                "class MoneySpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        if not code:\n"
                "            raise errors.invalid(\"bad_code\", \"code is empty\")\n"
                "        self.code = code\n",
                False,
            ),
            (
                "shop/domain/test_money.py",
                "shop.domain.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "shop/application/views.py",
                "shop.application.views",
                "import tesser.application as ts\n"
                "import shop.client.client as client\n"
                "import tesser.errors as errors\n"
                "class ViewService(ts.ApplicationService):\n"
                "    def ask(self, request: client.AskRequest) -> client.AskResponse:\n"
                "        raise errors.not_found(\"no_row\", request.text)\n",
                False,
            ),
            (
                "shop/application/test_views.py",
                "shop.application.test_views",
                "def test_views_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "shop/adapters/gateways.py",
                "shop.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import tesser.errors as errors\n"
                "class MemoryGateway(ts.Gateway):\n"
                "    def load(self, key: str) -> str:\n"
                "        raise errors.InfraError(key)\n",
                False,
            ),
            (
                "shop/adapters/test_gateways.py",
                "shop.adapters.test_gateways",
                "def test_gateways_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "member/domain/money.py",
                "member.domain.money",
                "import tesser.domain as ts\n"
                "from tesser.errors import invalid\n"
                "class MemberSpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = code\n",
                False,
            ),
            (
                "member/domain/test_money.py",
                "member.domain.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "stray/client/client.py",
                "stray.client.client",
                "import tesser.context as ts\n"
                "import tesser.errors as errors\n"
                "class AskRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "stray/client/test_client.py",
                "stray.client.test_client",
                "def test_client_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "astray/adapters/gateways.py",
                "astray.adapters.gateways",
                "import tesser.adapters as ts\n"
                "import tesser.serialization as serialization\n"
                "class StrayGateway(ts.Gateway):\n"
                "    def load(self, key: str) -> str:\n"
                "        return serialization.canonical_str(key)\n",
                False,
            ),
            (
                "astray/adapters/test_gateways.py",
                "astray.adapters.test_gateways",
                "def test_gateways_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert not any("shop.domain.money" in f for f in findings)
    assert not any("shop.application.views" in f for f in findings)
    assert not any("shop.adapters.gateways" in f for f in findings)
    assert any(
        "member.domain.money imports names from tesser.errors; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    )
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
        ("shop/adapters/eval_flat.py", "shop.adapters.eval_flat", body, False),
        ("shop/tests/__init__.py", "shop.tests", "", True),
        ("shop/tests/eval_tier.py", "shop.tests.eval_tier", body, False),
        ("shop/domain/eval_role.py", "shop.domain.eval_role", body, False),
    )
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=loose)).violations()
               )
    for outside in ("shop.adapters.eval_flat", "shop.tests.eval_tier", "shop.domain.eval_role"):
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
                "shop/adapters/gateways/__init__.py",
                "shop.adapters.gateways",
                "",
                True,
            ),
            (
                "shop/adapters/gateways/eval_llm.py",
                "shop.adapters.gateways.eval_llm",
                body,
                False,
            ),
            (
                "shop/adapters/gateways/llm/__init__.py",
                "shop.adapters.gateways.llm",
                "",
                True,
            ),
            (
                "shop/adapters/gateways/llm/evals/__init__.py",
                "shop.adapters.gateways.llm.evals",
                "",
                True,
            ),
            (
                "shop/adapters/gateways/llm/evals/eval_tools.py",
                "shop.adapters.gateways.llm.evals.eval_tools",
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
                "shop/adapters/handlers/http.py",
                "shop.adapters.handlers.http",
                "import tesser.adapters as ts\n"
                "import shop.client.client as client\n"
                "class Handler(ts.Handler):\n"
                "    def __init__(self, c: client.Client) -> None:\n"
                "        self._c = c\n",
                False,
            ),
            ("shop/adapters/handlers/__init__.py", "shop.adapters.handlers", "", True),
            ("shop/adapters/__init__.py", "shop.adapters", "", True),
            (
                "shop/adapters/handlers/test_http.py",
                "shop.adapters.handlers.test_http",
                "import tesser.testing as ts\n"
                "import shop.adapters.handlers.http as http\n"
                "import shop.client.client as client\n"
                "import shop.application.service as application\n"
                "import shop.adapters.gateways as gateways\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("shop/adapters/gateways/__init__.py", "shop.adapters.gateways", "", True),
        ))).violations()
               )
    assert any(
        "shop.adapters.handlers.test_http imports shop.application.service, but a test "
        "placed in handlers reaches only adapters.handlers, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "shop.adapters.handlers.test_http imports shop.adapters.gateways, but a test "
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
                "shop/adapters/handlers/http.py",
                "shop.adapters.handlers.http",
                "import tesser.adapters as ts\n"
                "import shop.client.client as client\n"
                "class Handler(ts.Handler):\n"
                "    def __init__(self, c: client.Client) -> None:\n"
                "        self._c = c\n",
                False,
            ),
            ("shop/adapters/handlers/__init__.py", "shop.adapters.handlers", "", True),
            ("shop/adapters/__init__.py", "shop.adapters", "", True),
            (
                "srv/test_router.py",
                "srv.test_router",
                "import tesser.testing as ts\n"
                "import shop.adapters.handlers.http as http\n"
                "import shop.application.service as application\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "srv.test_router imports shop.application.service, but a test placed in "
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
                "import shop.client.client as foreign\n"
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
        "far.domain.test_thing imports shop.client.client, but a test placed in domain "
        "reaches no neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )


def test_a_repository_sibling_test_reaches_its_kind_and_application_only() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/adapters/repositories/words.py",
                "shop.adapters.repositories.words",
                "import tesser.adapters as ts\n"
                "class WordsRepository(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self._rows: dict[str, str] = {}\n",
                False,
            ),
            (
                "shop/adapters/repositories/__init__.py",
                "shop.adapters.repositories",
                "",
                True,
            ),
            ("shop/adapters/__init__.py", "shop.adapters", "", True),
            (
                "shop/adapters/repositories/test_words.py",
                "shop.adapters.repositories.test_words",
                "import shop.adapters.repositories.words as words\n"
                "import shop.application.ports.words as words_port\n"
                "import shop.domain.thing as thing\n"
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
        "shop.adapters.repositories.test_words imports shop.domain.thing, but a test placed "
        "in repositories reaches only adapters.repositories, application.ports of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "shop.adapters.repositories.test_words imports far.client.client, but a test placed "
        "in repositories reaches no neighbouring context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_words.py:1:" in f for f in findings)
    assert not any("test_words.py:2:" in f for f in findings)


def test_a_component_sibling_test_mirrors_production_component_reach() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("shop/component/__init__.py", "shop.component", "", True),
            (
                "shop/component/component.py",
                "shop.component.component",
                "import tesser.component as ts\n"
                "class Wiring(ts.Component):\n"
                "    def close(self) -> None:\n"
                "        return None\n",
                False,
            ),
            (
                "shop/component/test_component.py",
                "shop.component.test_component",
                "import shop.application.service as service\n"
                "import far.client.client as farclient\n"
                "import shop.domain.thing as thing\n"
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
            (
                "far/client/test_client.py",
                "far.client.test_client",
                "def test_client_exists() -> None:\n"
                "    assert True\n",
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
            (
                "far/domain/test_thing.py",
                "far.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("far/domain/__init__.py", "far.domain", "", True),
        ))).violations()
               )
    assert any(
        "shop.component.test_component imports shop.domain.thing, but a test placed in component "
        "reaches only component, application, adapters, client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_component.py:1:" in f for f in findings)
    assert not any("test_component.py:2:" in f for f in findings)


def test_a_client_sibling_test_reaches_only_its_own_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/client/test_client.py",
                "shop.client.test_client",
                "import shop.client.client as client\n"
                "import shop.domain.thing as thing\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.client.test_client imports shop.domain.thing, but a test placed in client "
        "reaches only client of its own context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("test_client.py:1:" in f for f in findings)


def test_an_app_test_reaches_a_context_like_a_production_app() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/boot.py",
                "app.boot",
                "import tesser.context as ts\n"
                "def boot() -> int:\n"
                "    return 1\n",
                False,
            ),
            (
                "app/test_boot.py",
                "app.test_boot",
                "import shop.client.client as client\n"
                "import shop.domain.thing as thing\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("app/__init__.py", "app", "", True),
        ))).violations()
               )
    assert any(
        "app.test_boot imports shop.domain.thing, but a test placed in "
        "an app reaches a context only through its component, client, and adapters; "
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
                "import shop.client.client as client\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("protocol/__init__.py", "protocol", "", True),
        ))).violations()
               )
    assert any(
        "protocol.test_proto imports shop.client.client, but a test placed in "
        "protocol reaches no context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )


def test_a_test_that_resolves_to_no_tier_is_itself_a_finding() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/adapters/test_flat.py",
                "shop.adapters.test_flat",
                "def test_x() -> None:\n    assert True\n",
                False,
            ),
            (
                "shop/adapters/blobs/test_blob.py",
                "shop.adapters.blobs.test_blob",
                "def test_x() -> None:\n    assert True\n",
                False,
            ),
            ("shop/adapters/blobs/__init__.py", "shop.adapters.blobs", "", True),
            ("shop/adapters/__init__.py", "shop.adapters", "", True),
        ))).violations()
               )
    assert any(
        "shop.adapters.test_flat resolves to no test tier; "
        "a sibling test lives in a role package or an adapter kind package "
        "(handlers, gateways, repositories)" in f
        for f in findings
    )
    assert any(
        "shop.adapters.blobs.test_blob resolves to no test tier; "
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
            "import shop.application.service as neighbour\n"
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


def test_a_root_test_reaches_a_context_only_through_component_and_client() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/component/component.py",
                "shop.component.component",
                "import tesser.component as ts\n",
                False,
            ),
            (
                "tests/test_app.py",
                "tests.test_app",
                "import shop.client.client as client\n"
                "import shop.component.component as wire\n"
                "import shop.domain.thing as thing\n"
                "import shop.application.service as service\n"
                "import app.wire\n"
                "import tests.support\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "tests/support.py",
                "tests.support",
                "import shop.domain.thing as thing\n",
                False,
            ),
            ("app/wire.py", "app.wire", "", False),
        ))).violations()
               )
    reach = (
        "reaches a context only through its component and client; "
        "a test reaches only what its placement allows"
    )
    assert any(
        "tests.test_app imports shop.domain.thing, but a test placed in "
        "the root tests package reaches a context only through its component and client; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert any(
        "tests.test_app imports shop.application.service" in f and reach in f for f in findings
    )
    assert not any("tests.test_app imports shop.client.client" in f for f in findings)
    assert not any("tests.test_app imports shop.component.component" in f for f in findings)
    assert not any("tests.test_app imports app.wire" in f for f in findings)
    assert not any("tests.test_app imports tests.support" in f for f in findings)
    assert any(
        "tests.support is neither a test module nor conftest" in f for f in findings
    )
    assert any(
        f"tests.support imports shop.domain.thing, but a test placed in the root tests package {reach}" in f
        for f in findings
    )


def test_a_placed_test_reaches_the_app_shell_only_where_its_placement_does() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/test_thing.py",
                "shop.domain.test_thing",
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            (
                "srv/test_host.py",
                "srv.test_host",
                "import app.wire\n"
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
                "app/test_component.py",
                "app.test_component",
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            ("srv/http.py", "srv.http", "", False),
            ("app/wire.py", "app.wire", "", False),
        ))).violations()
               )
    clause = "does not reach that package; a test reaches only what its placement allows"
    assert any(
        "shop.domain.test_thing imports srv.http, but a test placed in domain "
        "does not reach that package; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("srv.test_host imports app.wire" in f for f in findings)
    assert any(
        "srv.test_host imports tests.test_root, but a test placed in srv "
        "does not reach that package" in f
        for f in findings
    )
    assert any(
        f"app.test_component imports srv.http, but a test placed in an app {clause}" in f
        for f in findings
    )


def test_a_context_tests_module_reaches_its_own_tests_package() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("shop/tests/__init__.py", "shop.tests", "", True),
            (
                "shop/tests/test_thing.py",
                "shop.tests.test_thing",
                "import shop.tests.conftest as helpers\n"
                "import two.tests.test_two as foreign\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
            ("shop/tests/conftest.py", "shop.tests.conftest", "", False),
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
    assert not any("shop.tests.test_thing imports shop.tests.conftest" in f for f in findings)
    assert any(
        "shop.tests.test_thing imports two.tests.test_two, but a test placed in tests "
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
                "import shop.domain.thing as thing\n"
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
                "shop/adapters/conftest.py",
                "shop.adapters.conftest",
                "import os\nimport shop.domain.thing\n",
                False,
            ),
            (
                "shop/conftest.py",
                "shop.conftest",
                "import shop.domain.thing\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.adapters.conftest imports shop.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert any(
        "shop.conftest imports shop.domain.thing; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    )
    assert not any("shop.adapters.conftest resolves to no test tier" in f for f in findings)
    assert not any("shop.adapters.conftest imports os" in f for f in findings)


def test_a_placed_conftest_carries_its_tier() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "tests/conftest.py",
                "tests.conftest",
                "import app.wire\nimport shop.domain.thing\n",
                False,
            ),
            ("shop/tests/__init__.py", "shop.tests", "", True),
            (
                "shop/tests/conftest.py",
                "shop.tests.conftest",
                "import shop.domain.thing as thing\nimport srv.http\n",
                False,
            ),
            ("app/wire.py", "app.wire", "", False),
            ("srv/http.py", "srv.http", "", False),
        ))).violations()
               )
    assert any(
        "tests.conftest imports shop.domain.thing, but a test placed in "
        "the root tests package reaches a context only through its component and client; "
        "a test reaches only what its placement allows" in f
        for f in findings
    )
    assert not any("tests.conftest imports app.wire" in f for f in findings)
    assert not any("shop.tests.conftest imports shop.domain.thing" in f for f in findings)
    assert any(
        "shop.tests.conftest imports srv.http, but a test placed in tests "
        "does not reach that package" in f
        for f in findings
    )


def test_adapter_kind_and_protocol_tests_shell_reach() -> None:
    kinds = ("handlers", "gateways", "repositories")
    adapters = tuple(
        entry
        for kind in kinds
        for entry in (
            (f"shop/adapters/{kind}/__init__.py", f"shop.adapters.{kind}", "", True),
            (
                f"shop/adapters/{kind}/test_{kind}.py",
                f"shop.adapters.{kind}.test_{kind}",
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
        "shop.adapters.handlers.test_handlers imports protocol.http" in f
        for f in findings
    ), f"a handlers-tier test was denied protocol: {findings}"
    for kind in ("gateways", "repositories"):
        assert any(
            f"shop.adapters.{kind}.test_{kind} imports protocol.http" in f
            and "does not reach that package" in f
            for f in findings
        ), f"a {kind} test reached protocol; only srv and handlers speak protocol: {findings}"
    for kind in ("handlers", "gateways", "repositories"):
        assert any(
            f"shop.adapters.{kind}.test_{kind} imports srv.http" in f
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
            ("shop/adapters/gateways/__init__.py", "shop.adapters.gateways", "", True),
            (
                "shop/adapters/gateways/eval_model.py",
                "shop.adapters.gateways.eval_model",
                "import protocol.http as http\n"
                "import srv.http\n"
                "def test_ok() -> None:\n    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.adapters.gateways.eval_model imports protocol.http" in f
        and "does not reach that package" in f
        for f in findings
    ), f"a gateway eval reached protocol; only srv and handlers speak protocol: {findings}"
    assert any(
        "shop.adapters.gateways.eval_model imports srv.http, but a test placed in gateways "
        "does not reach that package" in f
        for f in findings
    )


def test_a_context_tests_helper_answers_for_its_imports() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("shop/tests/__init__.py", "shop.tests", "", True),
            (
                "shop/tests/support.py",
                "shop.tests.support",
                "import shop.domain.thing as thing\nimport srv.http\n",
                False,
            ),
            ("srv/http.py", "srv.http", "", False),
        ))).violations()
               )
    assert any(
        "shop.tests.support is neither a test module nor conftest" in f for f in findings
    )
    assert any(
        "shop.tests.support imports srv.http, but a test placed in tests "
        "does not reach that package" in f
        for f in findings
    )
    assert not any("shop.tests.support imports shop.domain.thing" in f for f in findings)


def test_a_main_below_the_context_root_is_a_governed_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/__main__.py",
                "shop.domain.__main__",
                "import shop.application.service as service\n",
                False,
            ),
            ("shop/tests/__init__.py", "shop.tests", "", True),
            (
                "shop/tests/__main__.py",
                "shop.tests.__main__",
                "import shop.application.service as service\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.domain.__main__ imports shop.application.service; the same-context matrix is" in f
        for f in findings
    )
    assert any(
        "shop.tests.__main__ is neither a test module nor conftest" in f for f in findings
    )


def test_every_test_tier_has_a_shell_row() -> None:
    tiers = (
        set(checks.TEST_TIER_REACH)
        | {checks.SRV_TIER, checks.APP_TIER, checks.PROTOCOL_TIER, checks.APP_TIER}
    )
    assert tiers <= set(checks.TEST_TIER_SHELL)


def test_test_module_tesser_import_rules() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/test_imports.py",
                "shop.test_imports",
                "import tesser.domain as ts\n"
                "import tesser.testing as th\n"
                "import tesser.testing as ts2\n"
                "def test_nothing() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "shop/test_fromform.py",
                "shop.test_fromform",
                "from tesser.testing import fake\n"
                "def test_nothing() -> None:\n"
                "    assert fake is not None\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.test_imports imports tesser.domain; a test module's tesser imports "
        "are tesser.testing, tesser.errors, "
        "and tesser.serialization" in f
        for f in findings
    )
    assert any(
        "shop.test_imports imports tesser.testing without the ts alias; "
        "a test module imports tesser.testing at most once, as ts" in f
        for f in findings
    )
    assert any(
        "shop.test_imports imports tesser.testing again; "
        "a test module imports tesser.testing at most once, as ts" in f
        for f in findings
    )
    assert any(
        "shop.test_fromform imports names from tesser.testing; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
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
                "shop/test_junk.py",
                "shop.test_junk",
                "import tesser.testing as th\n"
                "def build() -> None:\n"
                "    return None\n"
                "class Junk:\n"
                "    pass\n"
                "@th.fake\n"
                "class FakeNothing:\n"
                "    pass\n"
                "class TestGrouped:\n"
                "    def test_inside(self) -> None:\n"
                "        assert True\n"
                "    def build_thing(self) -> None:\n"
                "        return None\n"
                "    async def drain_thing(self) -> None:\n"
                "        return None\n"
                "    async def test_async_inside(self) -> None:\n"
                "        assert True\n"
                "    def setup_method(self) -> None:\n"
                "        return None\n"
                "    class Nested:\n"
                "        pass\n"
                "    LABEL = 'x'\n"
                "class Tester:\n"
                "    def test_prefix_is_pytests(self) -> None:\n"
                "        assert True\n"
                "@th.fake\n"
                "class TestShapedFake:\n"
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
    assert any(
        "test_junk.Junk" in f
        and "a class in a test module is a Test-prefixed test class or declares itself with @ts.fake" in f
        for f in findings
    )
    assert any(
        "test_junk.TestGrouped.build_thing" in f and "a test class holds only test methods" in f
        for f in findings
    )
    assert any(
        "test_junk.TestGrouped.drain_thing" in f and "a test class holds only test methods" in f
        for f in findings
    )
    assert any(
        "test_junk.TestGrouped.setup_method" in f and "a test class holds only test methods" in f
        for f in findings
    )
    assert any(
        "test_junk.TestGrouped.Nested is a nested class" in f
        and "a test class holds test methods, never nested classes" in f
        for f in findings
    )
    assert any(
        "test_junk.TestGrouped carries a loose statement in its body" in f
        and "a test class holds test methods, never loose statements" in f
        for f in findings
    )
    assert not any("TB072" in f and "TestGrouped" in f for f in findings)
    assert not any("test_inside" in f for f in findings)
    assert not any("test_async_inside" in f for f in findings)
    assert not any("test_junk.Tester" in f for f in findings)
    assert any(
        "test_junk.TestShapedFake" in f and "a fake implements the contract it doubles" in f
        for f in findings
    )
    assert any("test_junk.FakeNothing" in f and "a fake implements the contract it doubles" in f for f in findings)
    assert any(
        "test_junk" in f and "a test module holds only imports, tests, helpers, and fakes" in f
        for f in findings
    )


def test_helper_rules_are_flagged() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/test_helpers.py",
                "shop.test_helpers",
                "import tesser.testing as th\n"
                "from shop.domain.thing import Thing, ThingSpec\n"
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
    assert any(
        "bad_builder" in f
        and "returns no construction data; a helper builds a spec or a DTO" in f
        for f in findings
    )
    assert any("bad_builder" in f and "has control flow" in f and "a helper only constructs" in f for f in findings)


def test_a_helper_builds_any_construction_data_but_never_a_protocol_or_a_domain_object() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/thing_reader.py",
                "shop.application.ports.thing_reader",
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class ReadThingRequest(ts.Request):\n"
                "    def __init__(self, thing_id: str) -> None:\n"
                "        self.thing_id = thing_id\n"
                "class ReadThingResponse(ts.Response):\n"
                "    def __init__(self, name: str) -> None:\n"
                "        self.name = name\n"
                "class ThingReader(ts.Port, Protocol):\n"
                "    def read(self, request: ReadThingRequest) -> ReadThingResponse: ...\n",
                False,
            ),
            (
                "shop/application/test_readers.py",
                "shop.application.test_readers",
                "import tesser.testing as th\n"
                "import shop.application.ports.thing_reader as thing_reader\n"
                "import shop.domain.thing as thing\n"
                "@th.helper\n"
                "def a_response(name: str = 'x') -> thing_reader.ReadThingResponse:\n"
                "    return thing_reader.ReadThingResponse(name=name)\n"
                "@th.helper\n"
                "def a_request(thing_id: str = 'x') -> thing_reader.ReadThingRequest:\n"
                "    return thing_reader.ReadThingRequest(thing_id=thing_id)\n"
                "@th.helper\n"
                "def a_port(name: str = 'x') -> thing_reader.ThingReader:\n"
                "    return thing_reader.ThingReader()\n"
                "@th.helper\n"
                "def a_domain_object(name: str = 'x') -> thing.Thing:\n"
                "    return thing.Thing(thing.ThingSpec(name=name))\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "a_response" in f and "a helper builds a spec or a DTO" in f for f in findings
    ), findings
    assert not any(
        "a_request" in f and "a helper builds a spec or a DTO" in f for f in findings
    ), findings
    assert any(
        "a_port" in f and "a helper builds a spec or a DTO" in f for f in findings
    )
    assert any(
        "a_domain_object" in f and "a helper builds a spec or a DTO" in f for f in findings
    )


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
                "shop/test_doors.py",
                "shop.test_doors",
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
    assert not any("shop.test_doors.FakeDoor" in f for f in findings)


def test_a_test_module_may_import_tesser_serialization_as_a_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/test_thing.py",
                "shop.domain.test_thing",
                "import tesser.serialization as serialization\n"
                "def test_canonical() -> None:\n"
                '    assert serialization.canonical_str("x") == "x"\n',
                False,
            ),
        ))).violations()
               )
    assert not any("shop.domain.test_thing" in f for f in findings)
    member = tuple(
                 f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                 for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/test_thing.py",
                "shop.domain.test_thing",
                "from tesser.serialization import canonical_str\n"
                "def test_canonical() -> None:\n"
                '    assert canonical_str("x") == "x"\n',
                False,
            ),
        ))).violations()
             )
    assert any(
        "shop.domain.test_thing imports names from tesser.serialization; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in member
    )


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
                "def test_a(monkeypatch) -> None:  # tesser:debt TB030\n"
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
                "shop/domain/bag.py",
                "shop.domain.bag",
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
                "shop/domain/holder.py",
                "shop.domain.holder",
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
                "shop/domain/leaky.py",
                "shop.domain.leaky",
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
        "the canonical exit is the only primitive exit" in f
        for f in findings
    )


def test_an_accessor_never_hands_back_the_backing_collection() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/box.py",
                "shop.domain.box",
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
                "shop/domain/pair.py",
                "shop.domain.pair",
                "import tesser.domain as ts\n"
                "import shop.domain.thing as thing\n"
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
                "shop/domain/exits.py",
                "shop.domain.exits",
                "import tesser.domain as ts\n"
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
                "shop/domain/shapes.py",
                "shop.domain.shapes",
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


def test_a_value_object_has_one_construction_path() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/doors.py",
                "shop.domain.doors",
                "import tesser.domain as ts\n"
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
        "TB017" in f and "Slug.parse is a second construction path; a value object has "
        "one construction path — its own __init__" in f
        for f in findings
    )


def test_domain_returns_and_spec_returns() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/returns.py",
                "shop.domain.returns",
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
                "shop/domain/pins.py",
                "shop.domain.pins",
                "import tesser.domain as ts\n"
                "from typing import ClassVar, Self\n"
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
    assert any("SelfDoor.parse is a second construction path" in f for f in findings)
    assert any("SelfDoor.bare_door is a second construction path" in f for f in findings)
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
                "shop/domain/policy.py",
                "shop.domain.policy",
                "import tesser.domain as ts\n"
                "def canonical_str(value: str) -> str:\n"
                "    return value\n",
                False,
            ),
            (
                "shop/domain/word.py",
                "shop.domain.word",
                "import tesser.domain as ts\n"
                "import shop.domain.policy as policy\n"
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
                "shop/domain/sack.py",
                "shop.domain.sack",
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


def test_a_debt_marker_suppresses_exactly_its_finding() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(("stray.py", "stray", "import os  # tesser:debt TB040\n", False),))).violations()
               )
    assert not any("stray" in f for f in findings)


def test_a_scoped_debt_marker_leaves_other_codes_alone() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(("stray.py", "stray", "import os  # tesser:debt TB050\n", False),))).violations()
               )
    assert any(
        "stray belongs to no governed package" in f and " TB040 " in f for f in findings
    )
    assert any(
        "stray.py:1: TB090" in f
        and "a debt marker suppresses an actual finding" in f
        for f in findings
    )


def test_a_stale_debt_marker_is_itself_a_finding() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/extra.py",
                "shop.domain.extra",
                "import tesser.domain as ts  # tesser:debt\n",
                False,
            ),
            (
                "shop/domain/test_extra.py",
                "shop.domain.test_extra",
                "def test_extra_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop/domain/extra.py:1: TB090" in f
        and "a debt marker suppresses an actual finding" in f
        for f in findings
    )


def test_a_file_level_debt_marker_covers_the_whole_module() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "srv/host.py",
                "srv.host",
                "# tesser:debt-file TB050\nimport os\n",
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
            ("stray.py", "stray", "import os  # tesser:debt TB040 TB050\n", False),
            ("loose.py", "loose", "import os  # tesser:debt TB040, TB050\n", False),
        ))).violations()
               )
    assert not any("stray" in f for f in findings)
    assert not any("loose" in f for f in findings)


def test_a_file_level_debt_marker_requires_codes() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(("stray.py", "stray", "import os  # tesser:debt-file\n", False),))).violations()
               )
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("stray.py:1: TB090" in f for f in findings)


def test_a_typo_or_junk_token_makes_the_marker_inert() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("stray.py", "stray", "import os  # tesser:debts TB040\n", False),
            (
                "loose.py",
                "loose",
                "import os  # tesser:debt TB040 permanent\n",
                False,
            ),
            ("bracket.py", "bracket", "import os  # tesser:debt [TB040]\n", False),
        ))).violations()
               )
    assert any("stray belongs to no governed package" in f for f in findings)
    assert any("loose belongs to no governed package" in f for f in findings)
    assert any("bracket belongs to no governed package" in f for f in findings)
    assert not any("stray.py" in f and "TB090" in f for f in findings)
    assert any("loose.py:1: TB090" in f for f in findings)
    assert any("bracket.py:1: TB090" in f for f in findings)


def test_a_bare_line_debt_marker_is_line_scoped() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/extra.py",
                "shop.domain.extra",
                "import os\nimport tesser.domain as ts  # tesser:debt\n",
                False,
            ),
        ))).violations()
               )
    assert any("shop.domain.extra imports os" in f and " TB062 " in f for f in findings)
    assert any("shop/domain/extra.py:2: TB090" in f for f in findings)


def test_tb090_itself_cannot_be_suppressed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/extra.py",
                "shop.domain.extra",
                "import tesser.domain as ts  # tesser:debt-file TB090\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop/domain/extra.py:1: TB090" in f
        and "a debt marker suppresses an actual finding" in f
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
    assert any("shop/domain/thing.py" not in f for f in findings)


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
                "# tesser:debt-file TB043\ndef f(:\n",
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
                "shop/application/ports.py",
                "shop.application.ports",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports is a ports module; ports is a package, never a module" in f
        for f in findings
    )


def test_a_ports_init_is_empty() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "X = 1\n",
                True,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports __init__ declares code; a ports __init__ is empty" in f
        for f in findings
    )


def test_a_ports_module_is_a_leaf() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/other.py",
                "shop.application.ports.other",
                "import tesser.application as ts\n"
                "class OtherSink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.application as ts\n"
                "import shop.domain.thing as thing\n"
                "import shop.application.ports.other as other\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports.sink imports shop.domain.thing; a ports module is a leaf "
        "and imports nothing from its tree, its own siblings included" in f
        for f in findings
    )
    assert any(
        "shop.application.ports.sink imports shop.application.ports.other; a ports module is a leaf "
        "and imports nothing from its tree, its own siblings included" in f
        for f in findings
    )


def test_a_ports_module_stdlib_allowlist() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink imports socket; a ports module imports "
        "only tesser.application and the pure stdlib" in f
        for f in findings
    )
    assert not any("imports enum;" in f for f in findings)


def test_a_ports_module_tesser_import_rules() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.domain as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/application/ports/plain.py",
                "shop.application.ports.plain",
                "import tesser.application\n"
                "class Plain(tesser.application.Port):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports.sink imports tesser.domain; "
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.application as ts\n"
                "FOUND = 'found'\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports.sink has a loose module-level statement; "
        "a ports module holds only imports and classes" in f
        for f in findings
    )


def test_a_ports_module_declares_exactly_one_port() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/two.py",
                "shop.application.ports.two",
                "import tesser.application as ts\n"
                "class First(ts.Port):\n"
                "    pass\n"
                "class Second(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/application/ports/none.py",
                "shop.application.ports.none",
                "import tesser.application as ts\n"
                "class Stray(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports.two declares 2 ports; a ports module "
        "declares exactly one port, so no two ports can share a request or a response" in f
        for f in findings
    )
    assert any(
        "shop.application.ports.none declares no port; a ports module "
        "declares exactly one port, so no two ports can share a request or a response" in f
        for f in findings
    )


def test_a_ports_module_holds_only_port_kinds() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Bare declares no ts.* base; a ports class declares its block" in f
        for f in findings
    )
    assert any(
        "shop.application.ports.sink.Leaked is a service; only a port and the requests "
        "and responses it speaks live in a ports module" in f
        for f in findings
    )


def test_a_port_method_speaks_one_request_and_one_response() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Sink.save parameter 'text' is not a ts.Request; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    )
    assert any(
        "shop.application.ports.sink.Sink.load does not return a ts.Response; "
        "a port method returns a ts.Response" in f
        for f in findings
    )
    assert any(
        "shop.application.ports.sink.Sink.both takes 2 parameters; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    )


def test_an_adapter_reaches_application_only_through_ports() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/adapters/gateways/memory.py",
                "shop.adapters.gateways.memory",
                "import tesser.adapters as ts\n"
                "import shop.application.ports.sink as sink\n"
                "import shop.application.service as service\n"
                "class MemorySink(ts.Repository):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.adapters.gateways.memory imports shop.application.service; "
        "the same-context matrix is a role to itself, application to domain and client, "
        "adapters to application/ports, component to application, adapters, and client" in f
        for f in findings
    )
    assert not any("imports shop.application.ports.sink;" in f for f in findings)


def test_a_port_dto_field_is_never_a_union() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.FindResponse.__init__ field 'item' is a union; "
        "a port DTO field is never a union, optional included — model the outcome as an enum" in f
        for f in findings
    )


def test_a_client_dto_field_may_still_be_optional() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/client/optional.py",
                "shop.client.optional",
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
    assert not any("shop.client.optional" in f and "is a union" in f for f in findings)


def test_a_conforming_ports_module_is_silent() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "import typing\n"
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
                "class Sink(ts.Port, typing.Protocol):\n"
                "    def save(self, request: SaveRequest) -> SaveResponse: ...\n"
                "    def all(self, request: ListRequest) -> SaveResponse: ...\n",
                False,
            ),
        ))).violations()
               )
    assert not any("shop/application/ports/sink.py" in f for f in findings), (
        f"a conforming ports module produced findings: "
        f"{[f for f in findings if 'ports/sink.py' in f]}"
    )


def test_a_ports_module_imports_a_module_never_names() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "from __future__ import annotations\n"
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class SaveRequest(ts.Request):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class SaveResponse(ts.Response):\n"
                "    def __init__(self, id: str) -> None:\n"
                "        self.id = id\n"
                "class Sink(ts.Port, Protocol):\n"
                "    def save(self, request: SaveRequest) -> SaveResponse: ...\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports.sink imports names from typing; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    ), findings


def test_a_ports_package_holds_only_ports_modules() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/application/ports/test_support.py",
                "shop.application.ports.test_support",
                "import tesser.testing as ts\n"
                "import shop.application.ports.sink as sink\n"
                "@ts.fake\n"
                "class Lookup(sink.Sink):\n"
                "    pass\n"
                "def test_x() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "shop/application/ports/conftest.py",
                "shop.application.ports.conftest",
                "",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports.test_support is not a ports module; a ports package holds "
        "only ports modules, and test_/eval_/conftest are reserved names, because a fake "
        "here would be an implementation adapters may import" in f
        for f in findings
    ), f"a fake could live in the package adapters may import: {findings}"
    assert any("shop.application.ports.conftest is not a ports module" in f for f in findings)


def test_a_client_dto_with_a_sibling_enum_stays_strict() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/client/verdict.py",
                "shop.client.verdict",
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
        "shop.client.verdict.VerdictResponse.__init__ parameter 'verdict' is not allowed; "
        "a DTO field is a primitive or another DTO" in f
        for f in findings
    )


def test_a_port_dto_field_is_never_a_bare_bool() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.FlagResponse.__init__ field 'found' is a bool; "
        "a port DTO field is never a bare bool — model the outcome as an enum" in f
        for f in findings
    )
    assert not any("'outcome'" in f for f in findings)


def test_a_port_dto_is_never_subclassed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.FoundItem subclasses a port DTO; a port DTO is never "
        "subclassed, because a response hierarchy is a union mypy cannot check for exhaustiveness" in f
        for f in findings
    )


def test_a_port_method_shape_survives_async_and_dunder_call() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Sink.fetch takes 2 parameters; "
        "a port method takes exactly one ts.Request" in f
        for f in findings
    ), f"async def bypassed the port shape rule: {findings}"
    assert any(
        "shop.application.ports.sink.Sink.__call__ parameter 'name' is not a ts.Request" in f
        for f in findings
    ), f"__call__ bypassed the port shape rule: {findings}"


def test_a_fake_implementing_a_port_may_expose_inspection_methods() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
                "shop/application/test_sink.py",
                "shop.application.test_sink",
                "import tesser.testing as ts\n"
                "import shop.application.ports.sink as sink\n"
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Loose is an enum.StrEnum; a ports enum is an enum.Enum, "
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Sink.save carries a body; a port method declares a shape "
        "and never a body, because a ports module holds no logic to import" in f
        for f in findings
    )
    assert not any("Sink.drop" in f for f in findings)


def test_a_debt_marked_ports_file_is_still_governed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports.py",
                "shop.application.ports",
                "import subprocess  # tesser:debt TB067\n"
                "import tesser.application as ts  # tesser:debt-file TB041\n"
                "import shop.domain.thing as thing\n"
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
        "shop.application.ports imports shop.domain.thing; a ports module is a leaf" in f
        for f in findings
    ), f"a debt-marked TB041 unlocked the module: {findings}"
    assert any("declares 2 ports" in f for f in findings)
    assert any("shop.application.ports.Leaked is a service" in f for f in findings)


def test_an_enum_base_cannot_hide_a_second_port() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/masked.py",
                "shop.application.ports.masked",
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
                "shop/application/ports/aliased.py",
                "shop.application.ports.aliased",
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
        "shop.application.ports.masked.Rules declares no ts.* base" in f for f in findings
    ), f"a name bound to something else was accepted as an enum: {findings}"
    assert not any("aliased.Outcome" in f for f in findings), (
        f"a properly bound enum alias was rejected: {findings}"
    )


def test_a_dynamic_import_is_not_a_way_around_the_matrix() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.application as ts\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
            (
                "shop/adapters/gateways/memory.py",
                "shop.adapters.gateways.memory",
                "import importlib\n"
                "import tesser.adapters as ts\n"
                "import shop.application.ports.sink as sink\n"
                "class MemorySink(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self._service = importlib.import_module('shop.application.service')\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.adapters.gateways.memory imports dynamically through importlib.import_module; "
        "an import is a statement the walk can read, never a call" in f
        for f in findings
    ), f"importlib walked around the import matrix: {findings}"


def test_a_dto_declares_its_fields_where_the_rules_can_read_them() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.ClassLevel carries a class-level statement; a port DTO "
        "declares its fields as __init__ parameters, where the field rules can read them" in f
        for f in findings
    ), f"a class-level bool field walked around the bare-bool rule: {findings}"
    assert any(
        "shop.application.ports.sink.Splatted.__init__ uses *args/**kwargs; a DTO declares "
        "its fields as named __init__ parameters, where the field rules can read them" in f
        for f in findings
    ), f"**kwargs walked around every DTO field rule: {findings}"


def test_an_async_method_on_a_dto_is_still_a_method() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Loaded.resolve defines a method on a DTO; "
        "a DTO carries data and nothing else" in f
        for f in findings
    ), f"async def carried logic onto a DTO: {findings}"


def test_a_nested_class_cannot_hide_a_second_port() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Holder.Second is a nested class; a ports module declares "
        "its port and its DTOs at module level, where the one-port count can see them" in f
        for f in findings
    ), f"a nested class hid a second port sharing every DTO: {findings}"


def test_a_dynamic_import_is_resolved_by_binding_not_spelling() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
                False,
            ),
            (
                "shop/adapters/gateways/memory.py",
                "shop.adapters.gateways.memory",
                "from importlib import import_module\n"
                "import tesser.adapters as ts\n"
                "import shop.application.ports.sink as sink\n"
                "class MemorySink(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self._service = import_module('shop.application.service')\n",
                False,
            ),
            (
                "shop/adapters/gateways/local.py",
                "shop.adapters.gateways.local",
                "import tesser.adapters as ts\n"
                "import shop.application.ports.sink as sink\n"
                "class LocalSink(ts.Repository):\n"
                "    def __init__(self, importlib: object) -> None:\n"
                "        self._loader = importlib\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.adapters.gateways.memory imports dynamically through importlib.import_module" in f
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Sink.bare names a shape it does not declare; a port "
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Sink carries a class-level statement; only an enum "
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Sink._score carries a body; a port method declares a "
        "shape and never a body" in f
        for f in findings
    ), f"a private method carried logic every implementer inherits: {findings}"


def test_a_stub_cannot_shadow_the_shape_the_rules_read() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
                False,
            ),
            (
                "shop/application/ports/sink.pyi",
                "shop.application.ports.sink",
                "import tesser.application as ts\n"
                "class Loose(ts.Response):\n"
                "    allowed: bool\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports.sink is a stub; a module carries its own shape, because a "
        "stub is what the type checker reads and the walk cannot" in f
        for f in findings
    ), f"a stub bypassed every ports rule at the type level: {findings}"


def test_a_ports_enum_carries_nothing_but_its_members() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Outcome carries more than its members; a ports enum "
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Validating.__init__ carries logic; a port DTO "
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Sink._raw is not a call an implementer provides; "
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Decorated is decorated; a ports module holds no "
        "decorator, because a decorator is a call that runs at import in the one "
        "application module adapters may import" in f
        for f in findings
    ), f"a decorator ran arbitrary code at import of the ports leaf: {findings}"
    assert any(
        "shop.application.ports.sink.Defaulted.__init__ carries a computed default; a ports "
        "module holds no expression that runs at import, because every adapter imports it" in f
        for f in findings
    ), f"a default parameter expression ran at import: {findings}"
    assert any(
        "shop.application.ports.sink.Computed computes a base; a ports module holds no "
        "expression that runs at import, and a base built by a call is logic every "
        "adapter imports" in f
        for f in findings
    ), f"a computed base ran at import: {findings}"
    assert any(
        "shop.application.ports.sink.Generic is generic; a ports module names concrete "
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
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Sink.audit carries a computed default; a ports module "
        "holds no expression that runs at import, because every adapter imports it" in f
        for f in findings
    ), f"an async def default expression ran at import: {findings}"


def test_a_port_dto_binds_only_its_own_parameters() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Capability.__init__ carries logic; a port DTO "
        "constructor only assigns its parameters" in f
        for f in findings
    ), f"a DTO bound a live capability an adapter could call: {findings}"
    assert not any("Plain" in f for f in findings)


def test_a_ports_class_carries_no_keyword() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Meta carries a class keyword; a ports module holds no "
        "expression that runs at import, and a metaclass is logic every adapter imports" in f
        for f in findings
    ), f"a metaclass ran logic at import of the ports leaf: {findings}"


def test_an_enum_member_may_be_negative_or_annotated() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.Outcome carries more than its members" in f
        for f in findings
    ), f"a dunder assignment laundered prose past the comments norm: {findings}"


def test_a_ports_module_computes_no_annotation() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.SaveRequest.__init__ computes an annotation; a ports "
        "module holds no expression that runs at import, and an annotation is evaluated "
        "like any other" in f
        for f in findings
    ), f"an annotation ran code at import of the ports leaf: {findings}"
    assert any(
        "shop.application.ports.sink.Sink.save is generic" in f for f in findings
    ), f"a generic port method went ungoverned: {findings}"


def test_every_spelling_of_a_dynamic_import_is_a_finding() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "import tesser.application as ts\nclass Sink(ts.Port):\n    pass\n",
                False,
            ),
            (
                "shop/adapters/gateways/rebound.py",
                "shop.adapters.gateways.rebound",
                "import importlib\n"
                "_load = importlib.import_module\n"
                "import tesser.adapters as ts\n"
                "import shop.application.ports.sink as sink\n"
                "class ReachRebound(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self.svc = _load('shop.application.service')\n",
                False,
            ),
            (
                "shop/adapters/gateways/indirect.py",
                "shop.adapters.gateways.indirect",
                "import importlib\n"
                "import tesser.adapters as ts\n"
                "import shop.application.ports.sink as sink\n"
                "class ReachIndirect(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self.svc = getattr(importlib, 'import_module')"
                "('shop.application.service')\n",
                False,
            ),
            (
                "shop/adapters/gateways/builtin.py",
                "shop.adapters.gateways.builtin",
                "import builtins\n"
                "import tesser.adapters as ts\n"
                "import shop.application.ports.sink as sink\n"
                "class ReachBuiltin(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self.svc = builtins.__import__('shop.application.service')\n",
                False,
            ),
            (
                "shop/adapters/gateways/registry.py",
                "shop.adapters.gateways.registry",
                "import sys\n"
                "import tesser.adapters as ts\n"
                "import shop.application.ports.sink as sink\n"
                "class ReachRegistry(ts.Repository):\n"
                "    def __init__(self) -> None:\n"
                "        self.svc = sys.modules['shop.application.service']\n",
                False,
            ),
        ))).violations()
               )
    for name in ("rebound", "indirect", "builtin", "registry"):
        assert any(f"shop.adapters.gateways.{name} imports dynamically" in f for f in findings), (
            f"the {name} spelling reached application with no import edge: {findings}"
        )


def test_a_ports_module_holds_only_shapes_the_rules_can_read() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
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
        "shop.application.ports.sink.SaveRequest.__init__ holds a Delete; a ports module "
        "holds only the shapes its rules can read, so anything else is a finding by "
        "default rather than a gap nobody enumerated" in f
        for f in findings
    ), f"a statement kind nobody enumerated passed silently: {findings}"
    assert any(
        "shop.application.ports.sink.Header holds a Subscript" in f for f in findings
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
    for taken in ("srv", "kernel", "tests", "protocol", "app"):
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
        for v in checks.Codebase(_spec(sources=(('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/__init__.py', 'kernel', 'import shop.domain.thing as thing\nX = 1\n', True)))).violations()
    )
    assert any(
        "kernel imports shop.domain.thing; "
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
    assert any("kernel constants are Final" in f for f in findings), findings
    assert any(
        "a kernel module holds classes, never functions" in f for f in findings
    ), findings
    assert any(
        "a kernel module holds only imports, classes, and Final constants" in f
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
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/prices.py', 'kernel.prices', 'import tesser.domain as ts\nfrom decimal import Decimal\nimport kernel.money\nimport shop.domain.thing\nimport requests\nclass PriceSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False)))).violations()
    )
    assert any(
        "kernel.prices imports shop.domain.thing; a kernel imports only its "
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
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False),
            (
                "kernel/test_money.py",
                "kernel.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ), ('shop/domain/price.py', 'shop.domain.price', 'import tesser.domain as ts\nimport kernel.money as money\nimport money_kernel\nclass Price(ts.ValueObject):\n    _money: money.Money\n    def __init__(self, amount: int) -> None:\n        object.__setattr__(self, "_money", money.Money(amount))\n', False),
            (
                "shop/domain/test_price.py",
                "shop.domain.test_price",
                "def test_price_exists() -> None:\n"
                "    assert True\n",
                False,
            )), imports=('money_kernel',))).violations()
    )
    assert not any("shop/domain/price.py" in f for f in findings), findings
    member = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        object.__setattr__(self, "_amount", amount)\n', False),
            (
                "kernel/test_money.py",
                "kernel.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ), ('shop/domain/price.py', 'shop.domain.price', 'import tesser.domain as ts\nfrom kernel.money import Money\nclass Price(ts.ValueObject):\n    _money: Money\n    def __init__(self, amount: int) -> None:\n        object.__setattr__(self, "_money", Money(amount))\n', False),
            (
                "shop/domain/test_price.py",
                "shop.domain.test_price",
                "def test_price_exists() -> None:\n"
                "    assert True\n",
                False,
            )))).violations()
    )
    assert any(
        "shop.domain.price imports names from kernel.money; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in member
    ), member


def test_an_undeclared_package_in_a_pure_role_is_still_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('shop/domain/price.py', 'shop.domain.price', 'import tesser.domain as ts\nimport money_kernel\nclass PriceSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False)))).violations()
    )
    assert any(
        "shop.domain.price imports money_kernel; domain, client, and application "
        "import only their context, their kernels, their tesser package, "
        "and the pure stdlib" in f
        for f in findings
    ), findings


def test_a_kernel_test_reaches_only_its_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/test_money.py', 'kernel.test_money', 'import tesser.testing as ts\nfrom kernel.money import Money\nimport shop.domain.thing\ndef test_money() -> None:\n    assert Money(1) == Money(1)\n', False)))).violations()
    )
    assert any(
        "kernel.test_money imports shop.domain.thing, but a test placed in "
        "a kernel reaches no context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    ), findings
    assert not any("imports kernel.money" in f for f in findings), findings


def test_an_exported_kernel_is_governed_like_a_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False),
            (
                "kernel/test_money.py",
                "kernel.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ), ('shells/__init__.py', 'shells', '', True), ('shells/svc.py', 'shells.svc', 'import tesser.domain as ts\nimport tesser.application as tsa\nclass Svc(tsa.ApplicationService):\n    pass\n', False),
            (
                "shells/test_svc.py",
                "shells.test_svc",
                "def test_svc_exists() -> None:\n"
                "    assert True\n",
                False,
            ), ('shop/domain/price.py', 'shop.domain.price', 'import tesser.domain as ts\nimport shells.svc as svc\nclass PriceSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False),
            (
                "shop/domain/test_price.py",
                "shop.domain.test_price",
                "def test_price_exists() -> None:\n"
                "    assert True\n",
                False,
            )), exports=('shells',))).violations()
    )
    assert any(
        "a kernel holds only domain kinds" in f for f in findings
    ), findings
    assert not any("shop/domain/price.py" in f for f in findings), findings


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
    for declared in ("srv", "kernel", "tests", "shop"):
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


def test_a_future_import_is_not_a_member_import() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "fut/domain/thing.py",
                "fut.domain.thing",
                "from __future__ import annotations\n"
                "import tesser.domain as ts\n"
                "class FutSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "fut/domain/test_thing.py",
                "fut.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
    )
    assert not any("fut.domain.thing" in f for f in findings), findings


@ts.helper
def _stdlib_spec(
    module: str = "collections",
    stdlib: tuple[str, ...] = ("collections", "typing", "enum"),
    pure_stdlib: tuple[str, ...] = (),
    extra: tuple[tuple[str, str, str | None, bool], ...] = (),
) -> checks.CodebaseSpec:
    return _spec(
        sources=(
            (
                "coll/domain/thing.py",
                "coll.domain.thing",
                "import tesser.domain as ts\n"
                f"import {module}\n"
                "class CollSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "coll/domain/test_thing.py",
                "coll.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            ("kernel/__init__.py", "kernel", "", True),
            (
                "kernel/money.py",
                "kernel.money",
                "import tesser.domain as ts\n"
                f"import {module}\n"
                "class Money(ts.ValueObject):\n"
                "    _amount: int\n"
                "    def __init__(self, amount: int) -> None:\n"
                '        object.__setattr__(self, "_amount", amount)\n',
                False,
            ),
            (
                "kernel/test_money.py",
                "kernel.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ) + extra,
        stdlib=stdlib,
        pure_stdlib=pure_stdlib,
    )


def test_a_stdlib_declaration_widens_the_domain_and_the_kernel() -> None:
    declared = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(
            _stdlib_spec(pure_stdlib=("collections",))
        ).violations()
    )
    assert declared == (), declared
    submodule = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_stdlib_spec(
            module="http.client",
            stdlib=("http", "typing", "enum"),
            pure_stdlib=("http",),
        )).violations()
    )
    assert submodule == (), submodule
    bare = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_stdlib_spec()).violations()
    )
    assert any(
        "coll.domain.thing imports collections; domain, client, and application "
        "import only their context, their kernels, their tesser package, "
        "and the pure stdlib" in f
        for f in bare
    ), bare
    assert any(
        "kernel.money imports collections; a kernel imports only its "
        "kernel, tesser.domain, declared kernels, and the pure stdlib" in f
        for f in bare
    ), bare


def test_a_stdlib_declaration_widens_neither_application_nor_client() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_stdlib_spec(
            pure_stdlib=("collections",),
            extra=(
                (
                    "coll/application/service.py",
                    "coll.application.service",
                    "import tesser.application as ts\n"
                    "import collections\n"
                    "class CollService(ts.ApplicationService):\n"
                    "    pass\n",
                    False,
                ),
                (
                    "coll/application/test_service.py",
                    "coll.application.test_service",
                    "def test_service_exists() -> None:\n"
                    "    assert True\n",
                    False,
                ),
                (
                    "coll/client/client.py",
                    "coll.client.client",
                    "import tesser.context as ts\n"
                    "import collections\n"
                    "class CollRequest(ts.Request):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
                (
                    "coll/client/test_client.py",
                    "coll.client.test_client",
                    "def test_client_exists() -> None:\n"
                    "    assert True\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any("coll.application.service imports collections" in f for f in findings), findings
    assert any("coll.client.client imports collections" in f for f in findings), findings
    assert not any("coll.domain.thing" in f for f in findings), findings


def test_a_stdlib_declaration_names_the_stdlib_and_widens_it_and_is_used() -> None:
    stray = (
        (
            "bad/domain/thing.py",
            "bad.domain.thing",
            "import tesser.domain as ts\n"
            "import requests\n"
            "class BadSpec(ts.Spec):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n",
            False,
        ),
        (
            "bad/domain/test_thing.py",
            "bad.domain.test_thing",
            "def test_thing_exists() -> None:\n"
            "    assert True\n",
            False,
        ),
    )
    external = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(
            _stdlib_spec(pure_stdlib=("requests",), extra=stray)
        ).violations()
    )
    assert external == (
        ".tesser-root:1: TB044 this tree declares 'stdlib requests' but that is "
        "not the stdlib; a stdlib declaration widens the domain's pure stdlib, "
        "an external package is declared with import",
    ), external
    repeated = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(
            _stdlib_spec(pure_stdlib=("typing",), extra=stray)
        ).violations()
    )
    assert repeated == (
        ".tesser-root:1: TB044 this tree declares 'stdlib typing' but the domain "
        "already imports it; a stdlib declaration widens the default pure stdlib, "
        "never repeats it",
    ), repeated
    unused = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_stdlib_spec(
            stdlib=("collections", "typing", "enum", "sqlite3"),
            pure_stdlib=("collections", "sqlite3"),
        )).violations()
    )
    assert unused == (
        ".tesser-root:1: TB044 this tree declares 'stdlib sqlite3' and nothing "
        "uses it; a stdlib declaration that legalizes nothing is itself a finding",
    ), unused


def test_a_stdlib_declaration_below_a_default_module_is_a_repeat() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_stdlib_spec(
            module="typing",
            pure_stdlib=("typing.io",),
        )).violations()
    )
    assert findings == (
        ".tesser-root:1: TB044 this tree declares 'stdlib typing.io' but the domain "
        "already imports it; a stdlib declaration widens the default pure stdlib, "
        "never repeats it",
    ), findings


def test_the_default_pure_stdlib_carries_the_shapes_a_domain_reaches_for() -> None:
    silent = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "wide/domain/thing.py",
                "wide.domain.thing",
                "import tesser.domain as ts\n"
                "import collections.abc\n"
                "import urllib.parse\n"
                "import copy\n"
                "class WideSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "wide/domain/test_thing.py",
                "wide.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
    )
    assert silent == (), silent
    loud = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "narrow/domain/thing.py",
                "narrow.domain.thing",
                "import tesser.domain as ts\n"
                "import urllib.request\n"
                "import collections\n"
                "class NarrowSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
            (
                "narrow/domain/test_thing.py",
                "narrow.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
    )
    assert any("narrow.domain.thing imports urllib.request" in f for f in loud), loud
    assert any("narrow.domain.thing imports collections;" in f for f in loud), loud


def test_a_kernel_module_imports_a_module_never_names() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            ("kernel/__init__.py", "kernel", "", True),
            (
                "kernel/money.py",
                "kernel.money",
                "import tesser.domain as ts\n"
                "from typing import Final\n"
                "class Money(ts.ValueObject):\n"
                "    _amount: int\n"
                "    def __init__(self, amount: int) -> None:\n"
                '        object.__setattr__(self, "_amount", amount)\n',
                False,
            ),
            (
                "kernel/test_money.py",
                "kernel.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ), stdlib=("typing",))).violations()
    )
    assert any(
        "kernel.money imports names from typing; every import is a "
        "module import — import x or import x as name, never from x "
        "import name" in f
        for f in findings
    ), findings


def test_kernel_siblings_import_each_other_in_both_kernel_shapes() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False),
            (
                "kernel/test_money.py",
                "kernel.test_money",
                "def test_money_exists() -> None:\n"
                "    assert True\n",
                False,
            ), ('shells/__init__.py', 'shells', '', True), ('shells/base.py', 'shells.base', 'import tesser.domain as ts\nclass BaseSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False),
            (
                "shells/test_base.py",
                "shells.test_base",
                "def test_base_exists() -> None:\n"
                "    assert True\n",
                False,
            ), ('shells/rich.py', 'shells.rich', 'import tesser.domain as ts\nimport shells.base as shellsbase\nclass RichSpec(ts.Spec):\n    def __init__(self, base: shellsbase.BaseSpec) -> None:\n        self.base = base\n', False),
            (
                "shells/test_rich.py",
                "shells.test_rich",
                "def test_rich_exists() -> None:\n"
                "    assert True\n",
                False,
            ), ('kernel/rates.py', 'kernel.rates', 'import tesser.domain as ts\nimport kernel.money as money\nclass Rate(ts.ValueObject):\n    _money: money.Money\n    def __init__(self, amount: int) -> None:\n        object.__setattr__(self, "_money", money.Money(amount))\n', False),
            (
                "kernel/test_rates.py",
                "kernel.test_rates",
                "def test_rates_exists() -> None:\n"
                "    assert True\n",
                False,
            )), exports=('shells',))).violations()
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
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('shop/domain/price.py', 'shop.domain.price', 'import tesser.domain as ts\nfrom kernel.money import Money\nfrom kernel.vendored.impure import Client\nclass PriceSpec(ts.Spec):\n    def __init__(self, money: Money) -> None:\n        self.money = money\n', False)))).violations()
    )
    assert any("imports kernel.vendored.impure" in f for f in findings), findings
    assert not any("imports kernel.money" in f for f in findings), findings


def test_a_pure_role_kernel_import_needs_the_kernel_to_exist() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(('shop/domain/price.py', 'shop.domain.price', 'import tesser.domain as ts\nfrom kernel.money import Money\nclass PriceSpec(ts.Spec):\n    def __init__(self, money: Money) -> None:\n        self.money = money\n', False),))).violations()
    )
    assert any(
        "shop.domain.price imports kernel.money; domain, client, and application "
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
        for v in checks.Codebase(_spec(sources=(('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('kernel/__init__.py', 'kernel', 'import kernelish.money as money\n', True), ('kernelish/__init__.py', 'kernelish', '', True), ('kernelish/money.py', 'kernelish.money', 'import shop.domain.thing\n', False)))).violations()
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
        for v in checks.Codebase(_spec(sources=(('kernel/__init__.py', 'kernel', '', True), ('kernel/money.py', 'kernel.money', 'import tesser.domain as ts\nclass Money(ts.ValueObject):\n    _amount: int\n    def __init__(self, amount: int) -> None:\n        if amount < 0:\n            raise ValueError(f"negative: {amount}")\n        object.__setattr__(self, "_amount", amount)\n', False), ('shells/__init__.py', 'shells', '', True), ('shells/base.py', 'shells.base', 'import tesser.domain as ts\nclass BaseSpec(ts.Spec):\n    def __init__(self, text: str) -> None:\n        self.text = text\n', False), ('kernel/test_money.py', 'kernel.test_money', 'import kernel.money as money\nimport shells.base as shellsbase\ndef test_money() -> None:\n    assert money.Money(1) == money.Money(1)\n    assert shellsbase.BaseSpec("x") is not None\n', False)), exports=('shells',))).violations()
    )
    assert not any("kernel/test_money.py" in f for f in findings), findings


def test_an_implementation_module_carries_exactly_one_sibling_test() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/money.py",
                "shop.domain.money",
                "import tesser.domain as ts\n"
                "class MoneySpec(ts.Spec):\n"
                "    def __init__(self, code: str) -> None:\n"
                "        self.code = code\n",
                False,
            ),
            (
                "shop/domain/test_thing.py",
                "shop.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.domain.money has no sibling test file; an implementation "
        "module carries exactly one test_<module>.py beside it" in f
        for f in findings
    )
    assert not any("shop.domain.thing has no sibling test" in f for f in findings)


def test_a_sibling_test_names_the_module_beside_it() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/test_thing.py",
                "shop.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "shop/domain/test_ghost.py",
                "shop.domain.test_ghost",
                "def test_ghost() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "shop/tests/__init__.py",
                "shop.tests",
                "",
                True,
            ),
            (
                "shop/tests/test_wired_flow.py",
                "shop.tests.test_wired_flow",
                "def test_flow() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.domain.test_ghost pairs with no implementation module; a sibling "
        "test file is named test_<module>.py for the module beside it" in f
        for f in findings
    )
    assert not any("shop.domain.test_thing pairs with no" in f for f in findings)
    assert not any("shop.tests.test_wired_flow pairs with no" in f for f in findings)


def test_a_declaration_only_module_needs_no_sibling_test() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/test_thing.py",
                "shop.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ), base=(
            (
                "shop/domain/thing.py",
                "shop.domain.thing",
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
                "shop/client/client.py",
                "shop.client.client",
                "import tesser.context as ts\n"
                "class AskRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class AskResponse(ts.Response):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "shop.client.client has no sibling test file" in f for f in findings
    )


def test_a_ports_module_and_an_init_need_no_sibling_test() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/test_thing.py",
                "shop.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "shop/application/test_service.py",
                "shop.application.test_service",
                "def test_service_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/asker.py",
                "shop.application.ports.asker",
                "from typing import Protocol\n"
                "import tesser.application as ts\n"
                "class AskPortRequest(ts.Request):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class AskPortResponse(ts.Response):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        self.text = text\n"
                "class Asker(ts.Port, Protocol):\n"
                "    def ask(self, request: AskPortRequest) -> AskPortResponse: ...\n",
                False,
            ),
        ))).violations()
               )
    assert not any(
        "asker has no sibling test file" in f for f in findings
    )
    assert not any(
        "shop.domain has no sibling test file" in f for f in findings
    )


@ts.helper
def _tesser_export_spec(
    sources: tuple[tuple[str, str, str | None, bool], ...] = (),
    exports: tuple[str, ...] = ("tesser",),
    base: tuple[tuple[str, str, str | None, bool], ...] = (
        ("tesser/__init__.py", "tesser", "", True),
        ("tesser/domain/__init__.py", "tesser.domain", "", True),
        (
            "tesser/domain/valueobject.py",
            "tesser.domain.valueobject",
            "class ValueObject:\n"
            "    def __eq__(self, other: object) -> bool:\n"
            "        return self.__dict__ == other.__dict__\n",
            False,
        ),
        (
            "tesser/domain/test_valueobject.py",
            "tesser.domain.test_valueobject",
            "import tesser.domain.valueobject as valueobject\n"
            "def test_equality() -> None:\n"
            "    assert valueobject.ValueObject() == valueobject.ValueObject()\n",
            False,
        ),
    ),
) -> checks.CodebaseSpec:
    return checks.CodebaseSpec(
        sources=base + sources,
        declared="app",
        nested=(),
        symlinked=(),
        exports=exports,
    )


def test_the_shells_tree_is_clean_and_not_context_shaped() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec()).violations()
    )
    assert findings == (), findings


def test_a_tesser_shell_module_imports_a_module_never_names() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                (
                    "tesser/domain/tag.py",
                    "tesser.domain.tag",
                    "from typing import Final\n"
                    "class Tag:\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
                (
                    "tesser/domain/test_tag.py",
                    "tesser.domain.test_tag",
                    "def test_tag_exists() -> None:\n"
                    "    assert True\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert findings == (
        "tesser/domain/tag.py:1: TB053 tesser.domain.tag imports names from typing; "
        "every import is a module import — import x or import x as name, "
        "never from x import name",
    ), findings


def test_a_tesser_init_only_reexports_from_the_distribution() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                (
                    "tesser/testing/__init__.py",
                    "tesser.testing",
                    "from tesser.testing.fake import fake as fake\n"
                    "from . import declared as declared\n"
                    "import subprocess\n"
                    "X = 1\n",
                    True,
                ),
                ("tesser/testing/fake.py", "tesser.testing.fake", "", False),
            ),
        )).violations()
    )
    assert any(
        "tesser.testing imports subprocess; "
        "a tesser __init__ only re-exports from the distribution" in f
        for f in findings
    ), findings
    assert any(
        "tesser.testing __init__ declares code; "
        "a tesser __init__ only re-exports from the distribution" in f
        for f in findings
    ), findings
    assert not any("imports tesser.testing.fake" in f for f in findings), findings
    assert not any("tesser.testing.declared" in f for f in findings), findings


def test_the_distribution_holds_only_consumer_namespaces() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(("tesser/extras.py", "tesser.extras", "X = 1\n", False),),
        )).violations()
    )
    assert any(
        "tesser.extras is not a consumer namespace; the tesser "
        "distribution holds only the namespaces its consumers import" in f
        for f in findings
    ), findings


def test_a_shell_module_stays_on_the_shell_stdlib() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                (
                    "tesser/srv/host.py",
                    "tesser.srv.host",
                    "import subprocess\n"
                    "from typing import Protocol\n"
                    "from tesser.domain.valueobject import ValueObject\n"
                    "class Host(Protocol):\n"
                    "    ...\n",
                    False,
                ),
                ("tesser/srv/__init__.py", "tesser.srv", "", True),
            ),
        )).violations()
    )
    assert any(
        "tesser.srv.host imports subprocess; a shell module imports "
        "only the tesser distribution and the shell stdlib" in f
        for f in findings
    ), findings
    assert not any("imports typing" in f for f in findings), findings
    assert not any("imports tesser.domain" in f for f in findings), findings


def test_the_shells_tests_probe_freely_with_any_tesser_import() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                (
                    "tests/test_shells.py",
                    "tests.test_shells",
                    "import tesser.adapters\n"
                    "import tesser.domain\n"
                    "class Probe(tesser.domain.ValueObject):\n"
                    "    pass\n"
                    "def test_probe() -> None:\n"
                    "    assert Probe() == Probe()\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert findings == (), findings


def test_the_shells_tests_keep_function_totality() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                (
                    "tests/test_shells.py",
                    "tests.test_shells",
                    "import tesser.domain\n"
                    "def helper() -> int:\n"
                    "    return 1\n"
                    "print('loose')\n"
                    "def test_ok() -> None:\n"
                    "    assert True\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "is neither a test nor a declared helper; a test module holds "
        "tests, @ts.helper builders, and @ts.fake doubles" in f
        for f in findings
    ), findings
    assert any(
        "a test module holds only imports, tests, helpers, and fakes" in f
        for f in findings
    ), findings


def test_a_tree_exporting_tesser_holds_nothing_else() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                (
                    "billing/domain/money.py",
                    "billing.domain.money",
                    "import tesser.domain as ts\n"
                    "class MoneySpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert len(findings) == 1, findings
    assert any(
        "a tree exporting tesser is the distribution itself — "
        "its top level is tesser and tests, nothing else" in f
        for f in findings
    ), findings


def test_a_stray_subpackage_in_the_distribution_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                (
                    "tesser/evil/__init__.py",
                    "tesser.evil",
                    "from tesser.domain.valueobject import ValueObject as ValueObject\n",
                    True,
                ),
            ),
        )).violations()
    )
    assert any(
        "tesser.evil is not a consumer namespace; the tesser "
        "distribution holds only the namespaces its consumers import" in f
        for f in findings
    ), findings


def test_a_conftest_leaf_counts_tesser_edges_in_the_exporting_tree() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                (
                    "conftest.py",
                    "conftest",
                    "import tesser.domain.valueobject\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "conftest imports tesser.domain.valueobject; "
        "a conftest is a leaf that imports nothing from its tree" in f
        for f in findings
    ), findings


def test_an_app_module_holds_only_app_kinds() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "app/wrong.py",
                "app.wrong",
                "import tesser.app as ts\n"
                "import tesser.component as tc\n"
                "class Slice(tc.Component):\n"
                "    pass\n"
                "class Root(ts.App):\n"
                "    pass\n",
                False,
            ),
            (
                "app/test_wrong.py",
                "shop.test_wrong",
                "def test_wrong_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "app.wrong.Slice is a component; only an app, an app loader, an app config, "
        "an app config spec, and a config repository live in an app module" in f
        for f in findings
    )
    assert not any("app.wrong.Root" in f and "TB052" in f for f in findings)


def test_a_component_releases_what_it_constructed() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "leaky/component/component.py",
                "leaky.component.component",
                "import tesser.component as ts\n"
                "class Leaky(ts.Component):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "class Tidy(ts.Component):\n"
                "    def __init__(self) -> None:\n"
                "        return None\n"
                "    def close(self) -> None:\n"
                "        return None\n",
                False,
            ),
            (
                "leaky/component/test_component.py",
                "leaky.component.test_component",
                "def test_wire_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "leaky.component.component.Leaky defines no close; "
        "a component releases what it constructed" in f
        for f in findings
    )
    assert not any("leaky.component.component.Tidy" in f for f in findings)


def test_a_config_constructs_from_exactly_one_spec() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "loose/component/config.py",
                "loose.component.config",
                "import tesser.component as ts\n"
                "class Spec(ts.Spec):\n"
                "    def __init__(self, storage: str) -> None:\n"
                "        self.storage = storage\n"
                "class Doorless(ts.Config):\n"
                "    pass\n"
                "class Wide(ts.Config):\n"
                "    def __init__(self, storage: str, extra: str) -> None:\n"
                "        self.storage = storage\n"
                "class Right(ts.Config):\n"
                "    def __init__(self, spec: Spec) -> None:\n"
                "        self.storage = spec.storage\n",
                False,
            ),
            (
                "loose/component/test_config.py",
                "loose.component.test_config",
                "def test_config_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "loose.component.config.Doorless defines no __init__; "
        "a config constructs from exactly one ts.Spec" in f
        for f in findings
    )
    assert any(
        "loose.component.config.Wide.__init__ takes 2 parameters; "
        "a config constructor takes exactly one ts.Spec" in f
        for f in findings
    )
    assert not any("loose.component.config.Right" in f for f in findings)


def test_a_do_not_use_tesser_module_is_not_a_consumer_namespace() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_tesser_export_spec(
            sources=(
                ("tesser/do_not_use_declared.py", "tesser.do_not_use_declared", "def function(fn: object) -> object:\n    return fn\n", False),
                ("tesser/test_do_not_use_declared.py", "tesser.test_do_not_use_declared", "def test_declared() -> None:\n    assert True\n", False),
                ("tesser/stray.py", "tesser.stray", "", False),
                ("tesser/test_stray.py", "tesser.test_stray", "def test_stray() -> None:\n    assert True\n", False),
            ),
        )).violations()
    )
    assert not any("tesser.do_not_use_declared is not a consumer namespace" in f for f in findings)
    assert any("tesser.stray is not a consumer namespace" in f for f in findings)


def test_a_sibling_method_reference_is_flagged_in_every_module_kind() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            ("shop/domain2.py", "shop.domain2", "", False),
            (
                "plain/domain/thing.py",
                "plain.domain.thing",
                "import tesser.domain as ts\n"
                "class Thing(ts.ValueObject):\n"
                "    _text: str\n"
                "    def __init__(self, text: str) -> None:\n"
                "        object.__setattr__(self, \"_text\", text)\n"
                "    def shout(self) -> str:\n"
                "        return self.spoken().upper()\n"
                "    def spoken(self) -> str:\n"
                "        return self._text\n"
                "    def walk(self, value: object) -> int:\n"
                "        if isinstance(value, tuple):\n"
                "            return sum(self.walk(item) for item in value)\n"
                "        return 1\n"
                "    def width(self, value: object) -> int:\n"
                "        return self.walk(value)\n",
                False,
            ),
            (
                "plain/domain/test_thing.py",
                "plain.domain.test_thing",
                "import tesser.testing as ts\n"
                "@ts.fake\n"
                "class FakeThing:\n"
                "    def poke(self) -> None:\n"
                "        return self.prod()\n"
                "    def prod(self) -> None:\n"
                "        return None\n"
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "plain.domain.thing.Thing.shout reaches sibling spoken; a method is for "
        "outsiders — a class reaches into itself only for direct recursion" in f
        for f in findings
    )
    assert any(
        "plain.domain.test_thing.FakeThing.poke reaches sibling prod; a method is for "
        "outsiders — a class reaches into itself only for direct recursion" in f
        for f in findings
    )
    assert not any("Thing.__init__" in f and "private method" in f for f in findings)


def test_a_domain_enum_is_a_primitive() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/state.py",
                "shop.domain.state",
                "import enum\n"
                "import tesser.domain as ts\n"
                "from tesser.serialization import canonical_str\n"
                "class LinkState(enum.Enum):\n"
                "    ACTIVE = 'active'\n"
                "    INACTIVE = 'inactive'\n"
                "class StatusSpec(ts.Spec):\n"
                "    def __init__(self, state: LinkState, note: LinkState | None, past: tuple[LinkState, ...]) -> None:\n"
                "        self.state = state\n"
                "        self.note = note\n"
                "        self.past = past\n"
                "class Status(ts.ValueObject):\n"
                "    _value: str\n"
                "    def __init__(self, value: LinkState) -> None:\n"
                "        object.__setattr__(self, '_value', value.value)\n"
                "    def __str__(self) -> str:\n"
                "        return canonical_str(self._value)\n",
                False,
            ),
            (
                "shop/domain/link.py",
                "shop.domain.link",
                "import tesser.domain as ts\n"
                "import shop.domain.state as state\n"
                "class LinkSpec(ts.Spec):\n"
                "    def __init__(self, status: state.LinkState) -> None:\n"
                "        self.status = status\n",
                False,
            ),
        ))).violations()
               )
    assert any("TB074" in f for f in findings)
    assert not any("LinkState declares no ts.* base" in f for f in findings)
    assert not any("parameter 'state' is not allowed" in f for f in findings)
    assert not any("parameter 'note' is not allowed" in f for f in findings)
    assert not any("parameter 'past' is not allowed" in f for f in findings)
    assert not any("parameter 'value' is not allowed" in f for f in findings)
    assert not any("parameter 'status' is not allowed" in f for f in findings)


def test_a_domain_enum_is_a_plain_enum() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/state.py",
                "shop.domain.state",
                "import enum\n"
                "import tesser.domain as ts\n"
                "class Loose(enum.StrEnum):\n"
                "    YES = 'yes'\n"
                "class LooseSpec(ts.Spec):\n"
                "    def __init__(self, x: Loose) -> None:\n"
                "        self.x = x\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.domain.state.Loose is an enum.StrEnum; a domain enum is an enum.Enum, "
        "because a str- or int-backed member compares equal to a raw literal "
        "and reopens the typo the enum closes" in f
        for f in findings
    )
    assert not any("parameter 'x' is not allowed" in f for f in findings)


def test_a_domain_enum_carries_nothing_but_its_members() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/state.py",
                "shop.domain.state",
                "import enum\n"
                "class LinkState(enum.Enum):\n"
                "    ACTIVE = 'active'\n"
                "    def label(self) -> str:\n"
                "        return 'x'\n"
                "@enum.unique\n"
                "class Tagged(enum.Enum):\n"
                "    A = 'a'\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.domain.state.LinkState carries more than its members; "
        "a domain enum is a closed set of names and nothing else, "
        "because an enum is a primitive with a name, "
        "not a home for behavior" in f
        for f in findings
    )
    assert any(
        "shop.domain.state.Tagged is decorated or keyworded; "
        "a domain enum is a bare class statement, "
        "because a decorator or a metaclass rewrites "
        "the primitive into a home for behavior" in f
        for f in findings
    )


def test_an_application_enum_still_declares_no_block() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/kinds.py",
                "shop.application.kinds",
                "import enum\n"
                "class Kind(enum.Enum):\n"
                "    A = 'a'\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.kinds.Kind declares no ts.* base; "
        "every context class declares its block" in f
        for f in findings
    )


def test_a_domain_enum_subclasses_enum_alone() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/state.py",
                "shop.domain.state",
                "import enum\n"
                "import tesser.domain as ts\n"
                "class Loose(str, enum.Enum):\n"
                "    YES = 'yes'\n"
                "class LooseSpec(ts.Spec):\n"
                "    def __init__(self, x: Loose) -> None:\n"
                "        self.x = x\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.domain.state.Loose mixes another base into its enum; a domain enum "
        "subclasses enum.Enum alone, because a str- or int-backed member "
        "compares equal to a raw literal and reopens the typo the enum closes" in f
        for f in findings
    )
    assert not any("parameter 'x' is not allowed" in f for f in findings)


def test_a_ports_enum_subclasses_enum_alone() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "import tesser.application as ts\n"
                "class Loose(str, enum.Enum):\n"
                "    YES = 'yes'\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.application.ports.sink.Loose mixes another base into its enum; a ports enum "
        "subclasses enum.Enum alone, because a str- or int-backed member "
        "compares equal to a raw literal and reopens the typo the enum closes" in f
        for f in findings
    )


def test_a_kernel_domain_enum_is_not_a_context_enum() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "kernel/domain/state.py",
                "kernel.domain.state",
                "import enum\n"
                "class LinkState(enum.Enum):\n"
                "    ACTIVE = 'active'\n",
                False,
            ),
            (
                "shop/domain/link.py",
                "shop.domain.link",
                "import tesser.domain as ts\n"
                "import kernel.domain.state as state\n"
                "class LinkSpec(ts.Spec):\n"
                "    def __init__(self, status: state.LinkState) -> None:\n"
                "        self.status = status\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "parameter 'status' is not allowed; "
        "a spec field is a primitive or a child spec, never a value object" in f
        for f in findings
    )


def test_an_enum_with_a_ts_base_is_its_declared_kind() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/state.py",
                "shop.domain.state",
                "import enum\n"
                "import tesser.domain as ts\n"
                "class Bad(enum.Enum, ts.ValueObject):\n"
                "    A = 'a'\n"
                "class BadSpec(ts.Spec):\n"
                "    def __init__(self, bad: Bad) -> None:\n"
                "        self.bad = bad\n",
                False,
            ),
        ))).violations()
               )
    assert not any("Bad declares no ts.* base" in f for f in findings)
    assert any(
        "parameter 'bad' is not allowed; "
        "a spec field is a primitive or a child spec, never a value object" in f
        for f in findings
    )


def test_an_enum_auto_member_is_a_member() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/ports/__init__.py",
                "shop.application.ports",
                "",
                True,
            ),
            (
                "shop/application/ports/sink.py",
                "shop.application.ports.sink",
                "from __future__ import annotations\n"
                "import enum\n"
                "from enum import auto\n"
                "import tesser.application as ts\n"
                "class Outcome(enum.Enum):\n"
                "    FOUND = auto()\n"
                "    MISSING = enum.auto()\n"
                "class Sink(ts.Port):\n"
                "    pass\n",
                False,
            ),
        ))).violations()
               )
    assert not any("carries more than its members" in f for f in findings)


def test_a_client_dto_still_rejects_a_domain_enum() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/state.py",
                "shop.domain.state",
                "import enum\n"
                "import tesser.domain as ts\n"
                "class LinkState(enum.Enum):\n"
                "    ACTIVE = 'active'\n",
                False,
            ),
            (
                "shop/client/view.py",
                "shop.client.view",
                "import tesser.context as ts\n"
                "import shop.domain.state as state\n"
                "class LinkView(ts.Response):\n"
                "    def __init__(self, status: state.LinkState) -> None:\n"
                "        self.status = status\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "parameter 'status' is not allowed; "
        "a DTO field is a primitive or another DTO" in f
        for f in findings
    )


def test_an_enum_wearing_a_dto_block_is_not_a_spec_field() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/state.py",
                "shop.domain.state",
                "import enum\n"
                "import tesser.context as tc\n"
                "import tesser.domain as ts\n"
                "class Weird(enum.Enum, tc.Request):\n"
                "    A = 'a'\n"
                "class WeirdSpec(ts.Spec):\n"
                "    def __init__(self, w: Weird) -> None:\n"
                "        self.w = w\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "parameter 'w' is not allowed; "
        "a spec field is a primitive or a child spec, never a value object" in f
        for f in findings
    )


def test_a_value_object_does_not_hand_back_a_domain_enum() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/state.py",
                "shop.domain.state",
                "import enum\n"
                "import tesser.domain as ts\n"
                "class LinkState(enum.Enum):\n"
                "    ACTIVE = 'active'\n"
                "class Status(ts.ValueObject):\n"
                "    _state: LinkState\n"
                "    def __init__(self, state: LinkState) -> None:\n"
                "        object.__setattr__(self, '_state', state)\n"
                "    def state(self) -> LinkState:\n"
                "        return self._state\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "shop.domain.state.Status.state passes the raw primitive through; "
        "a value object's accessor returns a value object" in f
        for f in findings
    )
    assert not any("Thing.walk" in f and "reaches sibling" in f for f in findings)
    assert not any("Thing.width" in f and "reaches sibling" in f for f in findings)
    assert not any("Thing.__init__" in f and "reaches sibling" in f for f in findings)
    assert not any("Thing.spoken" in f and "reaches sibling" in f for f in findings)


def test_a_spec_initializes_its_domain_object_and_does_nothing_else() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/tag.py",
                "shop.domain.tag",
                "import tesser.domain as ts\n"
                "class TagSpec(ts.Spec):\n"
                "    def __init__(self, value: str) -> None:\n"
                "        self.value = value\n"
                "class BagSpec(ts.Spec):\n"
                "    def __init__(self, tag: TagSpec) -> None:\n"
                "        self.tag = tag\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, spec: TagSpec) -> None:\n"
                "        object.__setattr__(self, '_value', spec.value)\n"
                "class Bag(ts.Entity):\n"
                "    def __init__(self, spec: BagSpec) -> None:\n"
                "        self._tag = Tag(spec.tag)\n"
                "        self._spec = spec\n"
                "    def retag(self, spec: TagSpec) -> None:\n"
                "        self._tag = Tag(spec)\n"
                "    def label(self, spec: TagSpec) -> str:\n"
                "        return spec.value\n",
                False,
            ),
            (
                "shop/adapters/handlers.py",
                "shop.adapters.handlers",
                "import tesser.adapters as ts\n"
                "import shop.domain.tag as tag\n"
                "class Keeper(ts.Handler):\n"
                "    def __init__(self, spec: tag.TagSpec) -> None:\n"
                "        object.__setattr__(self, '_spec', spec)\n"
                "    def peek(self) -> str:\n"
                "        built = tag.TagSpec(value='x')\n"
                "        return built.value\n"
                "    def forward(self) -> tag.Tag:\n"
                "        return tag.Tag(tag.TagSpec(value='y'))\n"
                "    def shadow(self, spec: tag.TagSpec) -> list:\n"
                "        return [spec.value for spec in ('a', 'b')]\n",
                False,
            ),
            (
                "shop/domain/test_tag.py",
                "shop.domain.test_tag",
                "import tesser.testing as ts\n"
                "import shop.domain.tag as tag\n"
                "@ts.helper\n"
                "def _spec() -> tag.TagSpec:\n"
                "    return tag.TagSpec(value='x')\n"
                "def test_reads_its_helper_spec() -> None:\n"
                "    spec = _spec()\n"
                "    assert tag.Tag(spec) is not None\n"
                "    assert spec.value == 'x'\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "shop/domain/tag.py:14: TB083 shop.domain.tag.Bag.__init__ keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/domain/tag.py:18: TB083 shop.domain.tag.Bag.label reads 'value' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/handlers.py:5: TB083 shop.adapters.handlers.Keeper.__init__ keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/handlers.py:8: TB083 shop.adapters.handlers.Keeper.peek reads 'value' of the spec 'built'; "
        "a spec is only read where it initializes its domain object",
    )


def test_a_spec_is_held_by_an_annotation_or_by_a_maker_function() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "mint/domain/coin.py",
                "mint.domain.coin",
                "import tesser.domain as ts\n"
                "class CoinSpec(ts.Spec):\n"
                "    def __init__(self, face: str) -> None:\n"
                "        self.face = face\n"
                "class Coin(ts.ValueObject):\n"
                "    def __init__(self, spec: CoinSpec) -> None:\n"
                "        object.__setattr__(self, '_face', spec.face)\n"
                "def make_coin_spec() -> CoinSpec:\n"
                "    return CoinSpec(face='h')\n"
                "def describe() -> str:\n"
                "    local = CoinSpec(face='t')\n"
                "    return local.face\n",
                False,
            ),
            (
                "mint/adapters/press.py",
                "mint.adapters.press",
                "import tesser.adapters as ts\n"
                "import mint.domain.coin as coin\n"
                "class Press(ts.Handler):\n"
                "    def annotated(self) -> str:\n"
                "        held: coin.CoinSpec = coin.make_coin_spec()\n"
                "        return held.face\n"
                "    def borrowed(self) -> str:\n"
                "        made = coin.make_coin_spec()\n"
                "        return made.face\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "mint/domain/coin.py:12: TB083 mint.domain.coin.describe reads 'face' of the spec 'local'; "
        "a spec is only read where it initializes its domain object",
        "mint/adapters/press.py:6: TB083 mint.adapters.press.Press.annotated reads 'face' of the spec 'held'; "
        "a spec is only read where it initializes its domain object",
        "mint/adapters/press.py:9: TB083 mint.adapters.press.Press.borrowed reads 'face' of the spec 'made'; "
        "a spec is only read where it initializes its domain object",
    )


def test_a_nested_parameter_named_for_the_spec_is_a_different_name() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "forge/domain/blade.py",
                "forge.domain.blade",
                "import tesser.domain as ts\n"
                "class BladeSpec(ts.Spec):\n"
                "    def __init__(self, edge: str) -> None:\n"
                "        self.edge = edge\n"
                "class Blade(ts.ValueObject):\n"
                "    def __init__(self, spec: BladeSpec) -> None:\n"
                "        object.__setattr__(self, '_edge', spec.edge)\n",
                False,
            ),
            (
                "forge/adapters/bench.py",
                "forge.adapters.bench",
                "import tesser.adapters as ts\n"
                "import forge.domain.blade as blade\n"
                "class Bench(ts.Handler):\n"
                "    def positional(self, spec: blade.BladeSpec) -> None:\n"
                "        def inner(spec: str, /) -> str:\n"
                "            return spec.edge\n"
                "        return None\n"
                "    def starred(self, spec: blade.BladeSpec) -> None:\n"
                "        def inner(*spec: str) -> str:\n"
                "            return spec.edge\n"
                "        return None\n"
                "    def doubled(self, spec: blade.BladeSpec) -> None:\n"
                "        def inner(**spec: str) -> str:\n"
                "            return spec.edge\n"
                "        return None\n"
                "    def keyworded(self, spec: blade.BladeSpec) -> None:\n"
                "        def inner(*, spec: str) -> str:\n"
                "            return spec.edge\n"
                "        return None\n"
                "    def lambdad(self, spec: blade.BladeSpec) -> None:\n"
                "        made = lambda spec: spec.edge\n"
                "        return None\n"
                "    def open_nested(self, spec: blade.BladeSpec) -> None:\n"
                "        def inner() -> str:\n"
                "            return spec.edge\n"
                "        return None\n"
                "    def open_lambda(self, spec: blade.BladeSpec) -> None:\n"
                "        made = lambda: spec.edge\n"
                "        return None\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "forge/adapters/bench.py:25: TB083 forge.adapters.bench.Bench.open_nested.inner reads 'edge' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "forge/adapters/bench.py:28: TB083 forge.adapters.bench.Bench.open_lambda reads 'edge' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
    )


def test_a_config_reads_its_spec_where_it_initializes_itself() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "shop/component/setup.py",
                "shop.component.setup",
                "import tesser.component as ts\n"
                "class SetupSpec(ts.Spec):\n"
                "    def __init__(self, host: str) -> None:\n"
                "        self.host = host\n"
                "class Setup(ts.Config):\n"
                "    def __init__(self, spec: SetupSpec) -> None:\n"
                "        self.host = spec.host\n"
                "    def echo(self, spec: SetupSpec) -> str:\n"
                "        return spec.host\n",
                False,
            ),
            (
                "app/boot.py",
                "app.boot",
                "import tesser.app as ts\n"
                "class BootSpec(ts.Spec):\n"
                "    def __init__(self, name: str) -> None:\n"
                "        self.name = name\n"
                "class Boot(ts.Config):\n"
                "    def __init__(self, spec: BootSpec) -> None:\n"
                "        self.name = spec.name\n"
                "    def echo(self, spec: BootSpec) -> str:\n"
                "        return spec.name\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "shop/component/setup.py:9: TB083 shop.component.setup.Setup.echo reads 'host' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "app/boot.py:9: TB083 app.boot.Boot.echo reads 'name' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
    )


def test_a_mapper_and_a_wider_spec_keep_only_what_they_assemble() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "shop/application/mapping.py",
                "shop.application.mapping",
                "import tesser.application as ts\n"
                "import shop.domain.thing as thing\n"
                "class Fold(ts.Mapper):\n"
                "    def __init__(self, spec: thing.ThingSpec) -> None:\n"
                "        self._spec = spec\n"
                "        object.__setattr__(self, '_twin', spec)\n"
                "    def unfold(self, spec: thing.ThingSpec) -> None:\n"
                "        self._spec = spec\n",
                False,
            ),
            (
                "shop/component/wiring.py",
                "shop.component.wiring",
                "import tesser.component as ts\n"
                "class InnerSpec(ts.Spec):\n"
                "    def __init__(self, host: str) -> None:\n"
                "        self.host = host\n"
                "class OuterSpec(ts.Spec):\n"
                "    def __init__(self, inner: InnerSpec) -> None:\n"
                "        self.inner = inner\n"
                "    def rewrap(self, inner: InnerSpec) -> None:\n"
                "        self.inner = inner\n",
                False,
            ),
            (
                "app/plan.py",
                "app.plan",
                "import tesser.app as ts\n"
                "class LegSpec(ts.Spec):\n"
                "    def __init__(self, name: str) -> None:\n"
                "        self.name = name\n"
                "class RunSpec(ts.Spec):\n"
                "    def __init__(self, leg: LegSpec) -> None:\n"
                "        self.leg = leg\n"
                "    def relay(self, leg: LegSpec) -> None:\n"
                "        self.leg = leg\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "shop/application/mapping.py:8: TB083 shop.application.mapping.Fold.unfold keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/component/wiring.py:9: TB083 shop.component.wiring.OuterSpec.rewrap keeps the spec 'inner'; "
        "a spec is never kept, it initializes its domain object and is done",
        "app/plan.py:9: TB083 app.plan.RunSpec.relay keeps the spec 'leg'; "
        "a spec is never kept, it initializes its domain object and is done",
    )


def test_a_comprehension_hides_the_spec_only_when_it_binds_the_name() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "shop/adapters/lister.py",
                "shop.adapters.lister",
                "import tesser.adapters as ts\n"
                "import shop.domain.thing as thing\n"
                "class Lister(ts.Handler):\n"
                "    def spread(self, spec: thing.ThingSpec) -> list:\n"
                "        return [spec.text for each in (1, 2)]\n"
                "    def paired(self, spec: thing.ThingSpec) -> dict:\n"
                "        return {each: spec.text for each in (1, 2)}\n"
                "    def genned(self, spec: thing.ThingSpec) -> object:\n"
                "        return (spec.text for each in (1, 2))\n"
                "    def setted(self, spec: thing.ThingSpec) -> set:\n"
                "        return {spec.text for each in (1, 2)}\n"
                "    def hidden(self, spec: thing.ThingSpec) -> set:\n"
                "        return {spec.text for spec in (1, 2)}\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "shop/adapters/lister.py:5: TB083 shop.adapters.lister.Lister.spread reads 'text' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/lister.py:7: TB083 shop.adapters.lister.Lister.paired reads 'text' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/lister.py:9: TB083 shop.adapters.lister.Lister.genned reads 'text' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/lister.py:11: TB083 shop.adapters.lister.Lister.setted reads 'text' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
    )


def test_one_line_reaching_for_the_spec_twice_is_reported_once() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "shop/adapters/twice.py",
                "shop.adapters.twice",
                "import tesser.adapters as ts\n"
                "import shop.domain.thing as thing\n"
                "class Twice(ts.Handler):\n"
                "    def read(self, spec: thing.ThingSpec) -> str:\n"
                "        return spec.text + spec.text\n"
                "    def hold(self, spec: thing.ThingSpec) -> None:\n"
                "        self.first = spec; self.second = spec\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "shop/adapters/twice.py:5: TB083 shop.adapters.twice.Twice.read reads 'text' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/twice.py:7: TB083 shop.adapters.twice.Twice.hold keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
    )


def test_writing_through_the_spec_is_not_reading_it() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "shop/adapters/hider.py",
                "shop.adapters.hider",
                "import tesser.adapters as ts\n"
                "import shop.domain.thing as thing\n"
                "class Hider(ts.Handler):\n"
                "    def nest(self, spec: thing.ThingSpec) -> object:\n"
                "        class Inner:\n"
                "            def peek(self) -> str:\n"
                "                return spec.text\n"
                "        return Inner\n"
                "    def write(self, spec: thing.ThingSpec) -> None:\n"
                "        spec.text = 'x'\n"
                "        return None\n"
                "    def deep(self, spec: thing.ThingSpec) -> str:\n"
                "        return spec.inner.text\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "shop/adapters/hider.py:7: TB083 shop.adapters.hider.Hider.nest.Inner.peek reads 'text' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/hider.py:13: TB083 shop.adapters.hider.Hider.deep reads 'inner' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
    )


def test_a_spec_is_read_through_a_keyword_a_guard_or_an_async_method() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "lace/domain/knot.py",
                "lace.domain.knot",
                "import tesser.domain as ts\n"
                "class KnotSpec(ts.Spec):\n"
                "    def __init__(self, loop: str) -> None:\n"
                "        self.loop = loop\n"
                "class Knot(ts.ValueObject):\n"
                "    def __init__(self, spec: KnotSpec) -> None:\n"
                "        object.__setattr__(self, '_loop', spec.loop)\n",
                False,
            ),
            (
                "lace/adapters/tie.py",
                "lace.adapters.tie",
                "import tesser.adapters as ts\n"
                "import lace.domain.knot as knot\n"
                "class Tie(ts.Handler):\n"
                "    def __init__(self, spec: knot.KnotSpec) -> None:\n"
                "        self.made = knot.Knot(spec.loop)\n"
                "    def keyworded(self, spec: knot.KnotSpec) -> object:\n"
                "        return dict(loop=spec.loop)\n"
                "    def guarded(self, spec: knot.KnotSpec) -> list:\n"
                "        return [each for each in (1, 2) if spec.loop]\n"
                "    async def awaited(self, spec: knot.KnotSpec) -> str:\n"
                "        return spec.loop\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "lace/adapters/tie.py:5: TB083 lace.adapters.tie.Tie.__init__ reads 'loop' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "lace/adapters/tie.py:7: TB083 lace.adapters.tie.Tie.keyworded reads 'loop' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "lace/adapters/tie.py:9: TB083 lace.adapters.tie.Tie.guarded reads 'loop' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "lace/adapters/tie.py:11: TB083 lace.adapters.tie.Tie.awaited reads 'loop' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
    )


def test_a_conftest_imports_modules_never_names() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "conftest.py",
                "conftest",
                "from __future__ import annotations\n"
                "from typing import Final\n"
                "import pathlib\n"
                "ROOT: Final[str] = str(pathlib.Path('.'))\n",
                False,
            ),
            (
                "shop/tests/conftest.py",
                "shop.tests.conftest",
                "from typing import Final\n"
                "SEEN: Final[int] = 1\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "conftest.py:2: TB053 conftest imports names from typing; every import is a "
        "module import — import x or import x as name, never from x import name" in f
        for f in findings
    )
    assert any(
        "shop/tests/conftest.py:1: TB053 shop.tests.conftest imports names from typing; "
        "every import is a module import" in f
        for f in findings
    )
    assert not any("imports names from __future__" in f for f in findings)
    assert not any("imports names from pathlib" in f for f in findings)


def test_a_nested_from_import_is_still_a_member_import() -> None:
    findings = tuple(
                   f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
                   for v in checks.Codebase(_spec(sources=(
            (
                "nest/domain/thing.py",
                "nest.domain.thing",
                "import tesser.domain as ts\n"
                "class ThingSpec(ts.Spec):\n"
                "    def __init__(self, text: str) -> None:\n"
                "        from decimal import Decimal\n"
                "        self.text = str(Decimal(text))\n",
                False,
            ),
            (
                "nest/domain/test_thing.py",
                "nest.domain.test_thing",
                "def test_thing_exists() -> None:\n"
                "    assert True\n",
                False,
            ),
        ))).violations()
               )
    assert any(
        "nest/domain/thing.py:4: TB053 nest.domain.thing imports names from decimal; "
        "every import is a module import" in f
        for f in findings
    )


def test_a_spec_is_tracked_through_aliases_stores_and_shadows() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/tag.py",
                "shop.domain.tag",
                "import tesser.domain as ts\n"
                "class TagSpec(ts.Spec):\n"
                "    def __init__(self, value: str) -> None:\n"
                "        self.value = value\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, spec: TagSpec) -> None:\n"
                "        object.__setattr__(self, '_value', spec.value)\n",
                False,
            ),
            (
                "shop/adapters/keeper.py",
                "shop.adapters.keeper",
                "import typing\n"
                "import tesser.adapters as ts\n"
                "import shop.domain.tag as tag\n"
                "def _quoted() -> 'tag.TagSpec':\n"
                "    return tag.TagSpec(value='x')\n"
                "class Keeper(ts.Handler):\n"
                "    def __init__(self, spec: tag.TagSpec) -> None:\n"
                "        self._direct = tag.TagSpec(value='x')\n"
                "        self._made = _quoted()\n"
                "        self._listed = [spec]\n"
                "        setattr(self, '_set', spec)\n"
                "        self._typed: tag.TagSpec = spec\n"
                "    def aliased(self, spec: tag.TagSpec) -> str:\n"
                "        alias = spec\n"
                "        again = alias\n"
                "        return again.value\n"
                "    def quoted(self, spec: 'tag.TagSpec') -> str:\n"
                "        return spec.value\n"
                "    def optional(self, spec: typing.Optional[tag.TagSpec]) -> str:\n"
                "        return spec.value if spec else ''\n"
                "    def reflected(self, spec: tag.TagSpec) -> object:\n"
                "        return (getattr(spec, 'value'), vars(spec))\n"
                "    def iterated(self, spec: tag.TagSpec) -> list:\n"
                "        return [x for spec in spec.items]\n"
                "    def looped(self, spec: tag.TagSpec) -> str:\n"
                "        for spec in ('a', 'b'):\n"
                "            return spec.upper()\n"
                "        return ''\n"
                "    def opened(self, spec: tag.TagSpec) -> str:\n"
                "        with open('f') as spec:\n"
                "            return spec.read()\n"
                "    def caught(self, spec: tag.TagSpec) -> object:\n"
                "        try:\n"
                "            return None\n"
                "        except ValueError as spec:\n"
                "            return spec.args\n"
                "    def replaced(self, spec: tag.TagSpec) -> str:\n"
                "        spec = 'plain'\n"
                "        return spec.upper()\n"
                "    def unrelated(self, value: int) -> int:\n"
                "        def inner() -> None:\n"
                "            value = tag.TagSpec(value='x')\n"
                "        return value.real\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "shop/adapters/keeper.py:8: TB083 shop.adapters.keeper.Keeper.__init__ keeps the spec 'tag.TagSpec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/keeper.py:9: TB083 shop.adapters.keeper.Keeper.__init__ keeps the spec '_quoted'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/keeper.py:10: TB083 shop.adapters.keeper.Keeper.__init__ keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/keeper.py:11: TB083 shop.adapters.keeper.Keeper.__init__ keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/keeper.py:12: TB083 shop.adapters.keeper.Keeper.__init__ keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/keeper.py:16: TB083 shop.adapters.keeper.Keeper.aliased reads 'value' of the spec 'again'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/keeper.py:18: TB083 shop.adapters.keeper.Keeper.quoted reads 'value' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/keeper.py:20: TB083 shop.adapters.keeper.Keeper.optional reads 'value' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/keeper.py:22: TB083 shop.adapters.keeper.Keeper.reflected reads '__dict__' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/keeper.py:22: TB083 shop.adapters.keeper.Keeper.reflected reads 'value' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/keeper.py:24: TB083 shop.adapters.keeper.Keeper.iterated reads 'items' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
    )


def test_a_spec_is_tracked_at_module_level_through_makers_mutators_and_match() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(sources=(
            (
                "shop/domain/tag.py",
                "shop.domain.tag",
                "import tesser.domain as ts\n"
                "class TagSpec(ts.Spec):\n"
                "    def __init__(self, value: str) -> None:\n"
                "        self.value = value\n"
                "class Tag(ts.ValueObject):\n"
                "    def __init__(self, spec: TagSpec) -> None:\n"
                "        object.__setattr__(self, '_value', spec.value)\n",
                False,
            ),
            (
                "shop/application/mapper.py",
                "shop.application.mapper",
                "import tesser.application as ts\n"
                "import shop.domain.tag as tag\n"
                "class MapToTagSpec(ts.Mapper):\n"
                "    def __init__(self, value: str) -> None:\n"
                "        self._value = value\n"
                "    def spec(self) -> tag.TagSpec:\n"
                "        return tag.TagSpec(value=self._value)\n",
                False,
            ),
            (
                "shop/adapters/top.py",
                "shop.adapters.top",
                "import tesser.adapters as ts\n"
                "import shop.domain.tag as tag\n"
                "import shop.application.mapper as mapper\n"
                "TOP = tag.TagSpec(value='x')\n"
                "SHOUT = TOP.value\n"
                "class Keeper(ts.Handler):\n"
                "    HELD = tag.TagSpec(value='y')\n"
                "    def __init__(self, m: mapper.MapToTagSpec, spec: tag.TagSpec, flag: bool) -> None:\n"
                "        self._made = m.spec()\n"
                "        self._either = spec if flag else TOP\n"
                "        self._items: list = []\n"
                "        self._items.append(spec)\n"
                "        self._links = set()\n"
                "        self._links.add(spec)\n"
                "        out = [(held := spec) for _ in range(1)]\n"
                "        self._held = held\n"
                "        self._value = TOP.value\n"
                "    def matched(self, spec: tag.TagSpec) -> str:\n"
                "        match [1]:\n"
                "            case [spec]:\n"
                "                return spec.upper()\n"
                "            case str() as spec:\n"
                "                return spec.upper()\n"
                "        return ''\n"
                "    def copied(self, spec: tag.TagSpec) -> object:\n"
                "        import copy\n"
                "        return copy.copy(spec)\n",
                False,
            ),
        ))).violations()
    )
    tb083 = tuple(f for f in findings if " TB083 " in f)
    assert tb083 == (
        "shop/adapters/top.py:4: TB083 shop.adapters.top keeps the spec 'tag.TagSpec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/top.py:5: TB083 shop.adapters.top reads 'value' of the spec 'TOP'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/top.py:7: TB083 shop.adapters.top.Keeper keeps the spec 'tag.TagSpec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/top.py:9: TB083 shop.adapters.top.Keeper.__init__ keeps the spec 'm.spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/top.py:10: TB083 shop.adapters.top.Keeper.__init__ keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/top.py:12: TB083 shop.adapters.top.Keeper.__init__ keeps the spec 'spec'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/top.py:16: TB083 shop.adapters.top.Keeper.__init__ keeps the spec 'held'; "
        "a spec is never kept, it initializes its domain object and is done",
        "shop/adapters/top.py:17: TB083 shop.adapters.top.Keeper.__init__ reads 'value' of the spec 'TOP'; "
        "a spec is only read where it initializes its domain object",
        "shop/adapters/top.py:27: TB083 shop.adapters.top.Keeper.copied reads '__dict__' of the spec 'spec'; "
        "a spec is only read where it initializes its domain object",
    )
