"""Ecosystem compatibility: mutation testing sees through ts.ValueObject.

Not a mutation-score gate. The claim under test is that building a value
object on ts.ValueObject leaves it fully visible to mutmut, while the
obvious alternative construction (a frozen dataclass) is skipped by mutmut
wholesale — hand-written methods included — so its behavior silently
escapes mutation testing. Both fixtures are the same Amount value object;
only the construction differs (test_fixtures_stay_in_lockstep enforces
that everything except vo/amount.py is byte-identical). mutmut is invoked
through its public CLI, pinned exact in requirements-dev.txt, because
these assertions describe observed behavior of that version: if an
upgrade changes either outcome, this test is the place that finds out.
The pin is best-effort — mutmut's own dependencies (libcst generates the
mutants, pytest runs them) float, so an upstream release can also move
these assertions; a red run here with no repo change means the ecosystem
moved, which is exactly what this test is for.
"""

import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

_FIXTURES = Path(__file__).parent / "fixtures"
_TESSER_PY = Path(__file__).resolve().parents[3]
assert (_TESSER_PY / "tesser" / "domain").is_dir(), (
    f"{_TESSER_PY} is not the tesser-py root — this module moved without "
    "updating its parents[] anchor"
)
_TRAMPOLINE_MARK = "@_mutmut_mutated"
# State a run leaves behind. Never copied into a fixture's tmp project:
# copytree preserves mtimes, and mutmut reuses a mutants/ tree that is newer
# than its source — a stale, gitignored mutants/ in the fixture dir would
# freeze this test green against a snapshot forever.
_JUNK_DIRS = ("mutants", "__pycache__", ".mypy_cache", ".pytest_cache")


def _run(
    args: "list[str]", cwd: Path, env: "dict[str, str]", timeout: int
) -> "subprocess.CompletedProcess[str]":
    # mutmut forks workers; on timeout, kill the whole session so a hung
    # worker does not outlive the test.
    proc = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        raise
    return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)


def _clean_env() -> "dict[str, str]":
    # The inner pytest (both the control run and mutmut's forked runner) must
    # not inherit the outer session's pytest/coverage configuration — an
    # allowlist keeps the subprocess contract ours. "." resolves against the
    # fixture project cwd (and, inside mutmut's runner, against mutants/ —
    # where mutmut chdirs; an internal but pinned behavior).
    env = {
        key: value
        for key, value in os.environ.items()
        if key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR")
    }
    env["PYTHONPATH"] = os.pathsep.join([str(_TESSER_PY), "."])
    return env


class _Outcome:
    def __init__(
        self,
        project: Path,
        env: "dict[str, str]",
        run: "subprocess.CompletedProcess[str]",
    ) -> None:
        self._project = project
        self._env = env
        self.run = run

    def results_output(self) -> str:
        results = _run(
            [sys.executable, "-m", "mutmut", "results"],
            cwd=self._project,
            env=self._env,
            timeout=20,
        )
        assert results.returncode == 0, results.stdout + results.stderr
        return results.stdout.strip()

    def mutants(self) -> str:
        mutants_file = self._project / "mutants" / "vo" / "amount.py"
        assert mutants_file.is_file(), (
            f"mutmut wrote no {mutants_file} — run output:\n"
            + self.run.stdout
            + self.run.stderr
        )
        return mutants_file.read_text()


def _mutmut_on(fixture: str, tmp_path: Path) -> _Outcome:
    project = tmp_path / fixture
    shutil.copytree(
        _FIXTURES / fixture, project, ignore=shutil.ignore_patterns(*_JUNK_DIRS)
    )
    env = _clean_env()

    # Control: the fixture suite must pass and actually collect tests under
    # plain pytest, or the dataclass assertions below would hold vacuously
    # (mutmut reports "no test case for any mutant" for an empty suite too).
    control = _run(
        [sys.executable, "-m", "pytest", "-q", "tests"],
        cwd=project,
        env=env,
        timeout=60,
    )
    assert control.returncode == 0, control.stdout + control.stderr
    collected = re.search(r"(\d+) passed", control.stdout)
    assert collected is not None and int(collected.group(1)) > 0, control.stdout

    # A zero exit from `mutmut run` means it did not crash — it says nothing
    # about survivors (verified: a suite that kills nothing still exits 0).
    # Survivor accounting is results_output()'s job.
    run = _run(
        [sys.executable, "-m", "mutmut", "run"],
        cwd=project,
        env=env,
        timeout=60,
    )
    return _Outcome(project, env, run)


def _fixture_files(root: Path) -> "dict[str, bytes]":
    files: "dict[str, bytes]" = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in _JUNK_DIRS for part in relative.parts):
            continue
        if path.is_file():
            files[str(relative)] = path.read_bytes()
    return files


def test_fixtures_stay_in_lockstep() -> None:
    tsvo = _fixture_files(_FIXTURES / "tsvo")
    dcvo = _fixture_files(_FIXTURES / "dcvo")
    assert set(tsvo) == set(dcvo), (
        "the fixtures hold different files — the comparison is apples-to-apples "
        f"only while their trees match: {sorted(set(tsvo) ^ set(dcvo))}"
    )
    diverged = sorted(
        name for name in tsvo if name != "vo/amount.py" and tsvo[name] != dcvo[name]
    )
    assert diverged == [], (
        f"{diverged} diverged between the fixtures — everything except "
        "vo/amount.py must stay byte-identical"
    )
    assert tsvo["vo/amount.py"] != dcvo["vo/amount.py"], (
        "the fixtures are supposed to differ in construction"
    )


def test_a_ts_valueobject_is_fully_visible_to_mutmut(tmp_path: Path) -> None:
    outcome = _mutmut_on("tsvo", tmp_path)
    assert outcome.run.returncode == 0, outcome.run.stdout + outcome.run.stderr
    mutants = outcome.mutants()
    for method in ("__init__", "add"):
        assert f"xǁAmountǁ{method}__mutmut_1" in mutants, (
            f"mutmut generated no mutants for Amount.{method}"
        )
    assert _TRAMPOLINE_MARK in mutants
    survivors = outcome.results_output()
    assert survivors == "", f"mutants escaped the fixture suite:\n{survivors}"


def test_a_dataclass_valueobject_is_skipped_by_mutmut_wholesale(tmp_path: Path) -> None:
    outcome = _mutmut_on("dcvo", tmp_path)
    output = outcome.run.stdout + outcome.run.stderr
    assert outcome.run.returncode != 0
    assert "could not find any test case for any mutant" in output
    mutants = outcome.mutants()
    assert "ǁAmountǁ" not in mutants
    assert _TRAMPOLINE_MARK not in mutants
    assert "def __post_init__" in mutants, (
        "the dataclass body should be carried over untouched, not dropped"
    )
