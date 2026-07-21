"""TB030 — the fakes-only test-double norm (``skills/tesser-build/testing.md``):
a test double is a hand-written fake that implements the collaborator's
interface, never a mocking library and never a runtime patcher. Banned
tree-wide (test and non-test code alike — domain/adapter code has no business
importing a mock library either):

* the mocking libraries — ``unittest.mock`` in every import shape, the PyPI
  ``mock`` backport, and the ``import unittest`` → ``unittest.mock.patch``
  attribute-chain evasion;
* pytest's ``monkeypatch`` builtin and ``MonkeyPatch`` type
  (``pytest.MonkeyPatch``, ``from pytest import MonkeyPatch``, a
  ``monkeypatch`` fixture parameter);
* pytest-mock's ``mocker`` fixture parameter.

There is deliberately no bare-``MonkeyPatch``-Name arm: for the import shapes
above it adds no detection power, while emitting a second finding per reference
and forcing a suppression marker onto every one of those lines.

**Known holes — this is a syntactic checker, not a resolver.** It reports what
it can see in one file's AST, and these shapes get through:

* an **aliased module import** — ``import unittest as u`` then ``u.mock.patch``,
  or ``import pytest as pt`` then ``pt.MonkeyPatch``. The attribute arms match
  the literal module name; closing this needs an alias table built in a first
  pass.
* **dynamic import** — ``importlib.import_module("unittest.mock")``,
  ``__import__``, ``getattr(unittest, "mock")``, ``sys.modules[...]``, or a
  star-import re-export.
* **use-site fixture access** — ``request.getfixturevalue("monkeypatch")``
  takes no banned parameter, so the fixture-parameter arm never sees it.
* a **suppressed import whitelists the module** — the mock-library arms fire on
  the import, not on each use, so one marker on the import line clears every
  call site below it.

They are tracked rather than papered over; each is a self-service bypass by an
author who could equally write the marker, which is why none of them blocks
shipping the rule.

Two scopes, on purpose. The **import** arms are global — domain and adapter
code have no business importing a mock library either, and global scope keeps
the ``bad.py`` fixture provable with ``is_test=False``. The **fixture-parameter**
arm is the check's one identifier-name signal, so it fires only inside a
pytest-shaped function (``test_*`` or a ``@fixture``-decorated factory): a
parameter named ``monkeypatch`` anywhere else is an ordinary name, and flagging
it would redden conformant code.

A wiring test that must patch a seam it cannot inject through carries an
explicit ``# tessercheck:ignore`` — a machine directive, comments-norm-exempt.
Suppression scans the reported node's whole line span, so the marker works on a
formatter-wrapped import as well as a single-line one.
"""

import ast
import io
import tokenize

from tessercheck.finding import Finding

_SUPPRESS_MARKER = "# tessercheck:ignore"

# A module whose import means a mocking library entered the file, in any import
# shape (``import X``, ``import X as y``, ``from X import ...``).
_MOCK_MODULES: frozenset[str] = frozenset({"unittest.mock", "mock"})


def _is_mock_module(module: str) -> bool:
    """Match a banned module or any submodule of one. Exact-string matching let
    real submodules through: ``mock.mock`` is a genuine module of the PyPI
    backport that re-exports ``patch``/``MagicMock``, and ``unittest.mock.mock``
    resolves too."""
    return any(
        module == banned or module.startswith(banned + ".")
        for banned in _MOCK_MODULES
    )


def _suppressed_lines(source: str) -> frozenset[int]:
    """Line numbers carrying a real ``# tessercheck:ignore`` COMMENT token.

    Tokenizing rather than substring-scanning the raw line is what stops a
    string literal that merely CONTAINS the marker text from silently
    suppressing a finding — ``SRC = '# tessercheck:ignore'`` is data, not a
    directive. On a tokenize failure this returns empty, so the check fails
    closed (findings are reported) rather than silently suppressing.
    """
    try:
        return frozenset(
            token.start[0]
            for token in tokenize.generate_tokens(io.StringIO(source).readline)
            if token.type == tokenize.COMMENT and _SUPPRESS_MARKER in token.string
        )
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return frozenset()

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
        "a hand-written fake through the seam instead of a runtime patcher; a "
        "wiring test that must patch a seam it cannot inject through carries "
        "'# tessercheck:ignore' (skills/tesser-build/testing.md)"
    )


def _is_pytest_shaped(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """A test function, or a fixture factory — the only places a parameter named
    ``mocker``/``monkeypatch`` is a pytest fixture injection rather than an
    ordinary identifier."""
    if node.name.startswith("test_"):
        return True
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Attribute) and target.attr == "fixture":
            return True
        if isinstance(target, ast.Name) and target.id == "fixture":
            return True
    return False


def check_test_doubles(path: str, source: str, tree: ast.Module) -> list[Finding]:
    """Every TB030 finding for one file. Global scope: fires in test and
    non-test code alike."""
    marked = _suppressed_lines(source)

    def suppressed(node: ast.AST) -> bool:
        # Scan the node's whole line span, not just its first line: a
        # formatter-wrapped `from unittest.mock import (\n ... \n)` reports at
        # the statement's start, so a marker on the closing line would
        # otherwise suppress nothing. Every node emitted here is small (an
        # import statement, an attribute, a single argument), so the span never
        # widens to a whole function body.
        start = int(getattr(node, "lineno", 0))
        end = int(getattr(node, "end_lineno", start) or start)
        return any(line in marked for line in range(start, end + 1))

    findings: list[Finding] = []

    def emit(node: ast.AST, message: str) -> None:
        line = int(getattr(node, "lineno", 0))
        col = int(getattr(node, "col_offset", 0)) + 1
        if suppressed(node):
            return
        findings.append(Finding(path, line, col, "TB030", message))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if _is_mock_module(module):
                emit(node, _MOCK_LIB_MSG)
            elif module == "unittest" and any(a.name == "mock" for a in node.names):
                emit(node, _MOCK_LIB_MSG)
            elif module in {"pytest", "_pytest.monkeypatch"} and any(
                a.name == "MonkeyPatch" for a in node.names
            ):
                emit(node, _MONKEYPATCH_MSG)
        elif isinstance(node, ast.Import):
            if any(_is_mock_module(a.name) for a in node.names):
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
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Scoped to a pytest-shaped function on purpose. This is the one
            # identifier-NAME signal in the check, and a parameter called
            # `mocker`/`monkeypatch` is a fixture injection only inside a test
            # or a fixture factory; anywhere else it is an ordinary name, and
            # flagging it would redden conformant production code. The
            # import-based arms above stay global — domain code has no business
            # importing a mock library either.
            if not _is_pytest_shaped(node):
                continue
            args = node.args
            for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                if arg.arg in _FIXTURE_PARAMS:
                    emit(arg, _fixture_msg(arg.arg))

    return findings
