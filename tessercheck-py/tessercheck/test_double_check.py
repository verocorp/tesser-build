"""TB030 — the fakes-only test-double norm (``skills/tesser-build/testing.md``):
a test double is a hand-written fake that implements the collaborator's
interface, never a mocking library and never a runtime patcher. Banned
tree-wide (test and non-test code alike — domain/adapter code has no business
importing a mock library either):

* the mocking libraries — ``unittest.mock`` in every import shape, the PyPI
  ``mock`` backport, and the ``import unittest`` → ``unittest.mock.patch``
  attribute-chain evasion;
* pytest's ``monkeypatch`` builtin and ``MonkeyPatch`` type
  (``pytest.MonkeyPatch``, ``from pytest import MonkeyPatch``, a bare
  ``MonkeyPatch`` reference, a ``monkeypatch`` fixture parameter);
* pytest-mock's ``mocker`` fixture parameter.

A wiring test that genuinely must patch a process seam carries an explicit
``# tessercheck:ignore`` — a machine directive, comments-norm-exempt. The
scope is global for the same reason TB020's is: the norm has no test exemption,
and global scope keeps the ``bad.py`` fixture provable with ``is_test=False``.
"""

import ast

from tessercheck.finding import Finding

_SUPPRESS_MARKER = "# tessercheck:ignore"

# A module whose import means a mocking library entered the file, in any import
# shape (``import X``, ``import X as y``, ``from X import ...``).
_MOCK_MODULES: frozenset[str] = frozenset({"unittest.mock", "mock"})

# pytest fixture parameter names that inject a runtime patcher rather than a
# hand-written fake: ``monkeypatch`` (builtin) and ``mocker`` (pytest-mock).
_FIXTURE_PARAMS: frozenset[str] = frozenset({"monkeypatch", "mocker"})

_MOCK_LIB_MSG = (
    "mocking library is banned (fakes-only test-double norm) — hand-write a "
    "fake that implements the collaborator's interface and inject it through "
    "the seam (skills/tesser-build/testing.md)"
)
_MONKEYPATCH_MSG = (
    "pytest monkeypatch/MonkeyPatch is banned (fakes-only test-double norm) — "
    "inject a hand-written fake through the seam instead of patching at "
    "runtime; a wiring test that must patch a process seam carries "
    "'# tessercheck:ignore' (skills/tesser-build/testing.md)"
)


def _fixture_msg(name: str) -> str:
    return (
        f"the {name!r} fixture is banned (fakes-only test-double norm) — inject "
        "a hand-written fake through the seam instead of a runtime patcher "
        "(skills/tesser-build/testing.md)"
    )


def check_test_doubles(path: str, source: str, tree: ast.Module) -> list[Finding]:
    """Every TB030 finding for one file. Global scope: fires in test and
    non-test code alike."""
    lines = source.splitlines()

    def suppressed(line: int) -> bool:
        return 1 <= line <= len(lines) and _SUPPRESS_MARKER in lines[line - 1]

    findings: list[Finding] = []

    def emit(node: ast.AST, message: str) -> None:
        line = int(getattr(node, "lineno", 0))
        col = int(getattr(node, "col_offset", 0)) + 1
        if suppressed(line):
            return
        findings.append(Finding(path, line, col, "TB030", message))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in _MOCK_MODULES:
                emit(node, _MOCK_LIB_MSG)
            elif module == "unittest" and any(a.name == "mock" for a in node.names):
                emit(node, _MOCK_LIB_MSG)
            elif module == "pytest" and any(
                a.name == "MonkeyPatch" for a in node.names
            ):
                emit(node, _MONKEYPATCH_MSG)
        elif isinstance(node, ast.Import):
            if any(a.name in _MOCK_MODULES for a in node.names):
                emit(node, _MOCK_LIB_MSG)
        elif isinstance(node, ast.Attribute):
            # ``unittest.mock`` reached without importing it directly (the
            # ``import unittest`` → ``unittest.mock.patch`` evasion).
            if (
                node.attr == "mock"
                and isinstance(node.value, ast.Name)
                and node.value.id == "unittest"
            ):
                emit(node, _MOCK_LIB_MSG)
            elif (
                node.attr == "MonkeyPatch"
                and isinstance(node.value, ast.Name)
                and node.value.id == "pytest"
            ):
                emit(node, _MONKEYPATCH_MSG)
        elif isinstance(node, ast.Name) and node.id == "MonkeyPatch":
            emit(node, _MONKEYPATCH_MSG)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            for arg in (
                *args.posonlyargs,
                *args.args,
                *args.kwonlyargs,
            ):
                if arg.arg in _FIXTURE_PARAMS:
                    emit(arg, _fixture_msg(arg.arg))

    return findings
