import ast
import json
from pathlib import Path

import tessercheck.adapters.repositories as repositories
import tessercheck.application.ports.source_reader as source_reader
import tessercheck.domain.checks as checks
import tessercheck.tests.conftest as conftest


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
    returned = conftest.returned_tokens(conftest.function_tree(checks.Codebase._locate))
    exercised = frozenset(expected for _, _, expected in table)
    assert returned == exercised, (
        f"the classification table and _locate's return set drifted apart: "
        f"unexercised tokens {sorted(returned - exercised)}, "
        f"stale table rows {sorted(exercised - returned)}"
    )


def test_every_location_token_has_a_dispatch_arm() -> None:
    tokens = conftest.returned_tokens(conftest.function_tree(checks.Codebase._locate))
    dispatch = conftest.function_tree(checks.Codebase._module_violations)
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


def test_every_place_is_earned_by_a_checked_tree_or_is_a_finding() -> None:
    finding_rows = (
        ("app.stray", False, "context-stray"),
        ("app.tests.util", False, "context-tests-stray"),
        ("app.application.ports.test_x", False, "ports-stray"),
        ("app.application.ports", False, "ports-file"),
        ("app.domain", False, "role-file"),
    )
    contexts = frozenset({"app"})
    for name, is_package, expected in finding_rows:
        got = checks.Codebase._locate(name, is_package, contexts)
        assert got == expected, (
            f"_locate({name!r}) = {got!r}, expected the finding place {expected!r}"
        )
    finding_places = frozenset(expected for _, _, expected in finding_rows)
    repo = Path(__file__).resolve().parents[3]
    manifest = json.loads((repo / "manifest.json").read_text(encoding="utf-8"))
    reader = repositories.FilesystemSourceReader()
    exercised: set[str] = set()
    checked_trees = 0
    for key, kind in sorted(manifest.items()):
        if kind != "app" or not (repo / key / ".tesser-root").is_file():
            continue
        checked_trees += 1
        read = reader.sources(source_reader.ReadSourcesRequest(root=str(repo / key)))
        names = [
            (s.name, s.form is source_reader.ModuleForm.PACKAGE) for s in read.sources
        ]
        tree_contexts = frozenset(
            name.split(".")[0]
            for name, _ in names
            if len(name.split(".")) >= 2 and name.split(".")[1] in checks.ROLES
        )
        for name, is_package in names:
            exercised.add(checks.Codebase._locate(name, is_package, tree_contexts))
    assert checked_trees >= 2, (
        f"only {checked_trees} checked trees found from {repo / 'manifest.json'}; "
        "this test must run from the tesser-build repo checkout"
    )
    tokens = conftest.returned_tokens(conftest.function_tree(checks.Codebase._locate))
    unearned = tokens - exercised - finding_places
    assert unearned == frozenset(), (
        f"_locate can produce {sorted(unearned)}, but no checked tree contains such "
        "a module and it is not a finding place; a classification exists only if a "
        "real tree earns it or a violation names it — an allowance the checker "
        "grants only itself is how context-main lived unnoticed for six releases"
    )
    assert not (finding_places & exercised), (
        f"a checked tree exercises the finding places "
        f"{sorted(finding_places & exercised)}; a tree passing the zero-findings "
        "gate should not contain violation-shaped modules"
    )
