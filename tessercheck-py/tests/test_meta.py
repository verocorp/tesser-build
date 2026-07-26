"""Meta-tests — the Python analog of ``TestEveryAnalyzerIsTested`` /
``TestNoUnregisteredAnalyzer``, plus the acceptance gate on ``examples/python``.
"""

import ast
from pathlib import Path

from tessercheck.checks import check_source
from tessercheck.finding import CHECKS, codes
from tessercheck.run import run_paths

_ROOT = Path(__file__).resolve().parents[2]
_PKG = Path(__file__).resolve().parents[1] / "tessercheck"
_TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
_EXAMPLES = _ROOT / "examples" / "python"


def test_every_check_has_a_good_and_bad_fixture() -> None:
    """File-scoped checks prove themselves with a good.py/bad.py pair;
    tree-scoped checks (whole-tree anatomy properties) with a
    good_tree/ / bad_tree/ directory pair. Either way: no check ships
    without its fixtures — the no-silent-gap guarantee covers both shapes."""
    for meta in CHECKS:
        d = _TESTDATA / meta.code.lower()
        if meta.scope == "file":
            assert (d / "good.py").is_file(), f"{meta.code} missing good.py fixture"
            assert (d / "bad.py").is_file(), f"{meta.code} missing bad.py fixture"
        elif meta.scope == "tree":
            for name in ("good_tree", "bad_tree"):
                tree_dir = d / name
                assert tree_dir.is_dir(), f"{meta.code} missing {name}/ fixture dir"
                assert list(tree_dir.rglob("*.py")), f"{meta.code} {name}/ has no .py files"
        else:
            raise AssertionError(f"{meta.code}: unknown scope {meta.scope!r}")


def test_tree_fixture_pairs_prove_their_check() -> None:
    """The teeth for tree-scoped checks: bad_tree/ must emit the check's code
    (the injected violation is caught) and good_tree/ must not (no false
    positive on the conformant shape). Fixture trees are checked as domain
    code — the harness injects a no-op test predicate because testdata/ paths
    are test-scoped by default."""
    def as_domain(_path: str) -> bool:
        return False

    for meta in CHECKS:
        if meta.scope != "tree":
            continue
        d = _TESTDATA / meta.code.lower()
        bad_findings, bad_errors = run_paths([str(d / "bad_tree")], is_test=as_domain)
        assert bad_errors == [], f"{meta.code} bad_tree: {bad_errors}"
        assert any(f.code == meta.code for f in bad_findings), (
            f"{meta.code}: bad_tree/ emitted no {meta.code} finding — the check has no teeth"
        )
        good_findings, good_errors = run_paths([str(d / "good_tree")], is_test=as_domain)
        assert good_errors == [], f"{meta.code} good_tree: {good_errors}"
        assert not any(f.code == meta.code for f in good_findings), (
            f"{meta.code}: good_tree/ emitted {meta.code} — false positive on the conformant shape"
        )


def test_tb031_fixture_pair_holds_its_contract_before_the_checker_ships() -> None:
    """TB031's checker is deliberately not built yet (fixtures-first), so it is
    not in CHECKS and the registry-keyed guards above never reach its fixtures.
    This is the interim owner: the pair must still DIFFER (the injected
    violation survives) and both trees must stay clean of every OTHER check, so
    that when TB031 lands the only delta is TB031 firing on bad_tree."""
    d = _TESTDATA / "tb031"
    good = (d / "good_tree" / "test_shortlink.py").read_text(encoding="utf-8")
    bad = (d / "bad_tree" / "test_shortlink.py").read_text(encoding="utf-8")
    assert good != bad, "tb031 fixtures converged — the pair no longer specifies a violation"

    def as_domain(_path: str) -> bool:
        return False

    for name in ("good_tree", "bad_tree"):
        findings, errors = run_paths([str(d / name)], is_test=as_domain)
        assert errors == [], f"{name}: {errors}"
        assert findings == [], f"{name}: " + "\n".join(f.render() for f in findings)


def test_tb032_bad_fixture_keeps_proving_the_class_based_walk() -> None:
    """The tb032 pair carries a second claim beyond good/bad, and nothing else
    would notice if it were lost.

    bad.py puts every one of its tests on a ``Test*`` class, so its module body
    holds no ``def test_*``. That is what makes it proof that TB032's test
    detection WALKS: a checker scanning ``tree.body`` would see no tests, exempt
    the file, and emit nothing — and the good/bad meta-tests would fail loudly.
    Adding a module-level ``def test_*`` to bad.py would keep every existing
    assertion green while silently retiring that proof, so pin the shape here.
    """
    bad = ast.parse((_TESTDATA / "tb032" / "bad.py").read_text(encoding="utf-8"))
    module_level = [
        n.name
        for n in bad.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("test_")
    ]
    assert module_level == [], (
        f"tb032/bad.py grew module-level tests {module_level} — it no longer "
        "proves that test detection walks past a Test* class"
    )
    in_class = [
        m.name
        for c in bad.body
        if isinstance(c, ast.ClassDef)
        for m in c.body
        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
        and m.name.startswith("test_")
    ]
    assert in_class, "tb032/bad.py has no class-based tests left to walk to"


def test_registry_codes_are_unique() -> None:
    seen = [c.code for c in CHECKS]
    assert len(seen) == len(set(seen))


def test_no_unregistered_code_is_emitted() -> None:
    registered = codes()
    for bad in _TESTDATA.glob("*/bad.py"):
        for f in check_source(str(bad), bad.read_text(encoding="utf-8"), is_test=False):
            assert f.code in registered, f"{bad} emitted unregistered {f.code}"


def test_acceptance_gate_examples_python_is_clean() -> None:
    # The examples are the canonical conformant tree — the analyzer must pass
    # clean on them, exactly as tessercheck gates examples/ddd on the Go side.
    assert _EXAMPLES.is_dir(), f"examples tree not found at {_EXAMPLES}"
    findings, errors = run_paths([str(_EXAMPLES)])
    assert findings == [], "\n".join(f.render() for f in findings)
    assert errors == [], "\n".join(errors)


def test_analyzer_passes_its_own_checks() -> None:
    # Dogfood: the analyzer's own source conforms. TB020 is excluded by
    # ruling: the comments norm governs constructed-app code and the example
    # templates; the toolkit's own internals are outside its governed scope
    # (skills/tesser-build/comments.md "Where the norm applies").
    findings, errors = run_paths([str(_PKG)])
    findings = [f for f in findings if f.code != "TB020"]
    assert findings == [], "\n".join(f.render() for f in findings)
    assert errors == [], "\n".join(errors)


class _QuoteAnnotations(ast.NodeTransformer):
    """Rewrite every annotation into its string-forward-reference form."""

    def _quote(self, ann: ast.expr | None) -> ast.expr | None:
        if ann is None or (isinstance(ann, ast.Constant) and isinstance(ann.value, str)):
            return ann
        return ast.copy_location(ast.Constant(value=ast.unparse(ann)), ann)

    def visit_arg(self, node: ast.arg) -> ast.arg:
        self.generic_visit(node)
        node.annotation = self._quote(node.annotation)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        node.returns = self._quote(node.returns)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        node.returns = self._quote(node.returns)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AnnAssign:
        self.generic_visit(node)
        annotation = self._quote(node.annotation)
        assert annotation is not None
        node.annotation = annotation
        return node


def test_quoting_every_annotation_changes_no_finding() -> None:
    # Metamorphic invariance over all four Python example trees: a string
    # annotation is the same annotation, so quoting every one of them must not
    # change a single finding. This is the whole-analyzer guard against the
    # walk re-diverging — when it had, this exact sweep produced TB015 on every
    # leaf value object in all four trees. Both sides are ast.unparse'd so
    # comment-carried markers (# tesser-category:) are stripped equally and
    # line numbers stay comparable. The comparison is a SET of (code, line) by
    # design: names inside one string share the string's position, so quoting
    # can merge two same-line reports of one reference into one — a position
    # artifact, not a lost finding. What the set contract does promise is that
    # no finding appears or disappears.
    trees = [_EXAMPLES, *(_ROOT / "examples" / t for t in ("python-app", "serdepy", "errorspy"))]
    paths = [p for tree in trees for p in sorted(tree.rglob("*.py"))]
    assert len(paths) > 100, "example trees have moved; fix the sweep's roots"
    for path in paths:
        src = path.read_text(encoding="utf-8")
        base = ast.unparse(ast.parse(src))
        quoted_tree = _QuoteAnnotations().visit(ast.parse(src))
        quoted = ast.unparse(ast.fix_missing_locations(quoted_tree))
        is_test = path.name.startswith("test_")
        base_findings = {(f.code, f.line) for f in check_source(str(path), base, is_test=is_test)}
        quoted_findings = {(f.code, f.line) for f in check_source(str(path), quoted, is_test=is_test)}
        assert base_findings == quoted_findings, (
            f"{path}: quoting annotations changed findings — "
            f"added {sorted(quoted_findings - base_findings)}, "
            f"lost {sorted(base_findings - quoted_findings)}"
        )
