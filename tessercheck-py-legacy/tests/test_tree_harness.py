"""The tree-fixture harness itself, proven live: ``run_paths`` with an
injected test-scoping predicate checks a fixture tree as domain code. Mirrors
exactly how tree-scoped checks' fixtures run — the tree dir is passed as the
run ROOT (so the ``testdata`` walk-prune never applies), while the files'
paths still contain ``testdata`` (so the DEFAULT predicate test-scopes them,
and the override is what makes them domain). This must work before the first
tree-scoped anatomy check lands."""

from pathlib import Path

from tessercheck.run import run_paths

_UNFROZEN = '''\
from dataclasses import dataclass


@dataclass
class Money:
    amount: int
    currency: str
'''


def _write_tree(tmp_path: Path) -> Path:
    tree = tmp_path / "testdata" / "tb999" / "bad_tree"
    pkg = tree / "campaign"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "values.py").write_text(_UNFROZEN, encoding="utf-8")
    return tree


def test_predicate_override_checks_tree_as_domain(tmp_path: Path) -> None:
    tree = _write_tree(tmp_path)
    findings, errors = run_paths([str(tree)], is_test=lambda _p: False)
    assert errors == []
    assert any(f.code == "TB001" for f in findings), (
        "predicate override should surface the unfrozen dataclass as domain code"
    )


def test_default_predicate_still_test_scopes(tmp_path: Path) -> None:
    tree = _write_tree(tmp_path)
    findings, _errors = run_paths([str(tree)])
    assert not any(f.code == "TB001" for f in findings), (
        "default scoping must keep exempting testdata paths — the override is opt-in"
    )
