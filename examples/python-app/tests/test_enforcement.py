"""The self-enforcement tests — the example enforces itself, so the shape it
teaches can't silently rot in a clone. These are real ``ast`` checks (not
string-grep, so comments/strings/generated code don't false-positive), scoped to
what the AST can actually prove:

  - the HOST is the env edge: ``os.getenv``/``os.environ`` calls are legal only in
    ``srv/*/main`` (there is no shared decoder — the host populates the spec-shaped
    ``Config`` and ``bootstrap.new`` validates it) — banned everywhere else;
  - only the edge exits (no ``sys.exit``/``os._exit`` below ``srv/*/main``);
  - no import-time side effects (module-level bare calls) in a context or bootstrap.

Each checker is also run on an INJECTED violation to prove it has teeth (per the
design's success criterion).
"""

from __future__ import annotations

import ast
import pathlib

from tests.discovery import discovered_contexts

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _parse(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _env_reads(tree: ast.Module) -> list[int]:
    hits: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "getenv"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
        ):
            hits.append(node.lineno)
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "environ"
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
        ):
            hits.append(node.lineno)
    return hits


def _exits(tree: ast.Module) -> list[int]:
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"exit", "_exit"}
            and isinstance(func.value, ast.Name)
            and func.value.id in {"sys", "os"}
        ):
            hits.append(node.lineno)
        if isinstance(func, ast.Name) and func.id in {"exit", "quit"}:
            hits.append(node.lineno)
    return hits


def _import_time_side_effects(tree: ast.Module) -> list[int]:
    hits: list[int] = []
    for stmt in tree.body:  # top level only
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            hits.append(stmt.lineno)  # a bare call at import time (a docstring is a Constant, skipped)
    return hits


def _py_files(*, exclude: set[pathlib.Path]) -> list[pathlib.Path]:
    return [
        p
        for p in ROOT.rglob("*.py")
        if p.resolve() not in exclude and "tests" not in p.parts and p.name != "conftest.py"
    ]


def _is_env_edge(rel: pathlib.PurePath) -> bool:
    """``srv/<host>/main.py`` — the host mains are the only legal env edge."""
    return len(rel.parts) == 3 and rel.parts[0] == "srv" and rel.parts[2] == "main.py"


def _env_offenders(files: list[tuple[str, ast.Module]]) -> dict[str, list[int]]:
    offenders: dict[str, list[int]] = {}
    for rel, tree in files:
        if _is_env_edge(pathlib.PurePosixPath(rel)):
            continue
        lines = _env_reads(tree)
        if lines:
            offenders[rel] = lines
    return offenders


def test_env_calls_only_in_srv_main() -> None:
    files = [(p.relative_to(ROOT).as_posix(), _parse(p)) for p in _py_files(exclude=set())]
    offenders = _env_offenders(files)
    assert not offenders, f"env access outside srv/*/main: {offenders}"


def test_only_the_edge_exits() -> None:
    edges = {(ROOT / "srv" / "http" / "main.py").resolve(), (ROOT / "srv" / "cli" / "main.py").resolve()}
    offenders: dict[str, list[int]] = {}
    for path in _py_files(exclude=edges):
        lines = _exits(_parse(path))
        if lines:
            offenders[str(path.relative_to(ROOT))] = lines
    assert not offenders, f"exit below srv/*/main: {offenders}"


def test_no_import_time_side_effects_in_contexts_or_bootstrap() -> None:
    # Contexts are DISCOVERED (tests/discovery.py), not enumerated — a new
    # context is covered by construction.
    offenders: dict[str, list[int]] = {}
    for pkg in (*discovered_contexts(), "bootstrap"):
        for path in (ROOT / pkg).rglob("*.py"):
            lines = _import_time_side_effects(_parse(path))
            if lines:
                offenders[str(path.relative_to(ROOT))] = lines
    assert not offenders, f"import-time side effect: {offenders}"


def test_checkers_flag_injected_violations() -> None:
    # Teeth: each checker fires on a deliberately-planted violation.
    assert _env_reads(ast.parse("import os\nx = os.getenv('CAMPAIGN_STORAGE')\n"))
    assert _env_reads(ast.parse("import os\ny = os.environ['X']\n"))
    assert _exits(ast.parse("import sys\ndef f() -> None:\n    sys.exit(1)\n"))
    assert _exits(ast.parse("import os\nos._exit(0)\n"))
    assert _import_time_side_effects(ast.parse("configure_logging()\n"))


def test_env_edge_scoping_teeth() -> None:
    # Teeth for the flipped rule: the same injected env call is flagged in a
    # context / wiring / bootstrap module and allowed in a host main.
    getenv_call = ast.parse("import os\nx = os.getenv('CAMPAIGN_STORAGE')\n")
    environ_read = ast.parse("import os\ny = os.environ['X']\n")
    assert _env_offenders([("campaign/wiring/wire.py", getenv_call)])
    assert _env_offenders([("bootstrap/bootstrap.py", environ_read)])
    assert _env_offenders([("linkpolicy/application/service.py", getenv_call)])
    assert not _env_offenders([("srv/http/main.py", getenv_call)])
    assert not _env_offenders([("srv/cli/main.py", environ_read)])
