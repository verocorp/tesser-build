import json
from pathlib import Path

import tessercheck.adapters.repositories as repositories
import tessercheck.application.ports.source_reader as source_reader
import tessercheck.domain.checks as checks
import tessercheck.tests.conftest as conftest


def test_every_place_is_earned_by_a_checked_tree_or_is_a_finding() -> None:
    finding_rows = (
        ("homeless", False, "root"),
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
