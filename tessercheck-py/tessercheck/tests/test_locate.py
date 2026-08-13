import ast
import inspect

import tessercheck.domain.checks as checks


def test_locate_is_the_single_routing_decision() -> None:
    contexts = frozenset({"app", "two"})
    table = (
        ("solo", False, "root"),
        ("test_solo", False, "test"),
        ("eval_solo", False, "eval"),
        ("conftest", False, "conftest"),
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
        ("tests.__main__", False, "root-tests"),
        ("tests.eval_x", False, "eval"),
        ("tests.conftest", False, "conftest"),
        ("srv", True, "shell-init"),
        ("srv.http", False, "shell"),
        ("srv.__main__", False, "shell"),
        ("srv.conftest", False, "conftest"),
        ("srv.deep.handler", False, "shell"),
        ("bootstrap.wire", False, "shell"),
        ("bootstrap.__main__", False, "shell"),
        ("protocol", True, "protocol-init"),
        ("protocol.http", False, "protocol"),
        ("protocol.__main__", False, "protocol"),
        ("protocol.conftest", False, "conftest"),
        ("app", True, "context-init"),
        ("app.__main__", False, "context-main"),
        ("app.domain", True, "role-init"),
        ("app.domain", False, "role-file"),
        ("app.domain.thing", False, "role"),
        ("app.domain.__main__", False, "role"),
        ("app.domain.sub.deep", False, "role"),
        ("app.domain.test_thing", False, "test"),
        ("app.domain.eval_bad", False, "eval"),
        ("app.domain.conftest", False, "conftest"),
        ("app.adapters.gateways.__main__", False, "role"),
        ("app.adapters.conftest", False, "conftest"),
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
    source = inspect.getsource(checks.Codebase._locate)
    tree = ast.parse("def f() -> None:\n" + "\n".join("    " + line for line in source.splitlines()[2:]))
    expected_tokens = {expected for _, _, expected in table}
    returned = {
        value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Return) and node.value is not None
        for value in ast.walk(node.value)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    }
    assert returned <= expected_tokens, (
        f"_locate can return tokens the classification table never exercises: "
        f"{sorted(returned - expected_tokens)}"
    )


def test_every_location_token_has_a_dispatch_arm() -> None:
    locate_source = inspect.getsource(checks.Codebase._locate)
    locate_tree = ast.parse(
        "def f() -> None:\n" + "\n".join("    " + line for line in locate_source.splitlines()[2:])
    )
    tokens = {
        value.value
        for node in ast.walk(locate_tree)
        if isinstance(node, ast.Return) and node.value is not None
        for value in ast.walk(node.value)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    }
    dispatch_source = inspect.getsource(checks.Codebase._module_violations)
    dispatch_tree = ast.parse(
        "def f() -> None:\n" + "\n".join("    " + line for line in dispatch_source.splitlines()[6:])
    )
    handled = {
        node.comparators[0].value
        for node in ast.walk(dispatch_tree)
        if isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == "place"
        and isinstance(node.comparators[0], ast.Constant)
    }
    assert tokens, "no tokens extracted from _locate"
    unhandled = tokens - handled - {"context-stray"}
    assert unhandled == set(), (
        f"_locate can return tokens with no dispatch arm: {sorted(unhandled)} "
        "(context-stray is the dispatch's final return)"
    )
