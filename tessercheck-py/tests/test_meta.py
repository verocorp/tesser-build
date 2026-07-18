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
    for meta in CHECKS:
        d = _TESTDATA / meta.code.lower()
        assert (d / "good.py").is_file(), f"{meta.code} missing good.py fixture"
        assert (d / "bad.py").is_file(), f"{meta.code} missing bad.py fixture"


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
