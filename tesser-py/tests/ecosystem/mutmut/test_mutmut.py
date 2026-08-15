"""Ecosystem compatibility: mutation testing sees through ts.ValueObject.

Not a mutation-score gate. The claim under test is that building a value
object on ts.ValueObject leaves it fully visible to mutmut, while the
obvious alternative construction (a frozen dataclass) is skipped by mutmut
wholesale — hand-written methods included — so its behavior silently
escapes mutation testing. Both fixtures are the same Amount value object;
only the construction differs. mutmut is invoked through its public CLI,
pinned in requirements-dev.txt, because these assertions describe observed
behavior of that version: if an upgrade changes either outcome, this test
is the place that finds out.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

_FIXTURES = Path(__file__).parent / "fixtures"
_TESSER_PY = Path(__file__).resolve().parents[3]
_TRAMPOLINE_MARK = "@_mutmut_mutated"


class _Outcome:
    def __init__(
        self,
        run: "subprocess.CompletedProcess[str]",
        results: "subprocess.CompletedProcess[str]",
        mutants: str,
    ) -> None:
        self.run = run
        self.results = results
        self.mutants = mutants


def _mutmut_on(fixture: str, tmp_path: Path) -> _Outcome:
    project = tmp_path / fixture
    shutil.copytree(_FIXTURES / fixture, project)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(_TESSER_PY), "."])
    run = subprocess.run(
        [sys.executable, "-m", "mutmut", "run"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    results = subprocess.run(
        [sys.executable, "-m", "mutmut", "results"],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    mutants = (project / "mutants" / "vo" / "amount.py").read_text()
    return _Outcome(run, results, mutants)


def test_a_ts_valueobject_is_fully_visible_to_mutmut(tmp_path: Path) -> None:
    outcome = _mutmut_on("tsvo", tmp_path)
    assert outcome.run.returncode == 0, outcome.run.stdout + outcome.run.stderr
    for method in ("__init__", "add"):
        assert f"xǁAmountǁ{method}__mutmut_1" in outcome.mutants, (
            f"mutmut generated no mutants for Amount.{method}"
        )
    assert _TRAMPOLINE_MARK in outcome.mutants
    survivors = outcome.results.stdout.strip()
    assert survivors == "", f"mutants escaped the fixture suite:\n{survivors}"


def test_a_dataclass_valueobject_is_skipped_by_mutmut_wholesale(tmp_path: Path) -> None:
    outcome = _mutmut_on("dcvo", tmp_path)
    output = outcome.run.stdout + outcome.run.stderr
    assert outcome.run.returncode != 0
    assert "could not find any test case for any mutant" in output
    assert "ǁAmountǁ" not in outcome.mutants
    assert _TRAMPOLINE_MARK not in outcome.mutants
    assert "def __post_init__" in outcome.mutants, (
        "the dataclass body should be carried over untouched, not dropped"
    )
