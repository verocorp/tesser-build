from __future__ import annotations

import ast
import inspect
import textwrap
from collections.abc import Callable

import tesser.testing as ts

import tessercheck.domain.checks as checks


@ts.helper
def _function_tree(func: Callable[..., object] = checks.Codebase._locate) -> ast.FunctionDef:  # tessercheck:ignore TB073
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef))


@ts.helper
def _returned_tokens(func: ast.FunctionDef | None = None) -> frozenset[str]:  # tessercheck:ignore TB073
    node = func if func is not None else _function_tree()
    return frozenset(
        value.value
        for stmt in ast.walk(node)
        if isinstance(stmt, ast.Return) and stmt.value is not None
        for value in ast.walk(stmt.value)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
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
    )
    for name, is_package, expected in table:
        got = checks.Codebase._locate(name, is_package, contexts)
        assert got == expected, (
            f"_locate({name!r}, is_package={is_package}) = {got!r}, expected {expected!r}"
        )
    returned = _returned_tokens()
    exercised = frozenset(expected for _, _, expected in table)
    assert returned == exercised, (
        f"the classification table and _locate's return set drifted apart: "
        f"unexercised tokens {sorted(returned - exercised)}, "
        f"stale table rows {sorted(exercised - returned)}"
    )


def test_every_location_token_has_a_dispatch_arm() -> None:
    tokens = _returned_tokens()
    dispatch = _function_tree(checks.Codebase._module_violations)
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
