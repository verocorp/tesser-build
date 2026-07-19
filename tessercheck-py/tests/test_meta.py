"""Meta-tests — the Python analog of ``TestEveryAnalyzerIsTested`` /
``TestNoUnregisteredAnalyzer``, plus the acceptance gate on ``examples/python``.
"""

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
    # Dogfood: the analyzer's own source conforms.
    findings, errors = run_paths([str(_PKG)])
    assert findings == [], "\n".join(f.render() for f in findings)
    assert errors == [], "\n".join(errors)
