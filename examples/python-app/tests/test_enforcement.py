"""The self-enforcement tests — the example enforces itself, so the shape it
teaches can't silently rot in a clone. These are real ``ast`` checks (not
string-grep, so comments/strings/generated code don't false-positive), scoped to
what the AST can actually prove:

  - env is read at ONE edge only (``config.py``) — nowhere else, not even a host main;
  - only the edge exits (no ``sys.exit``/``os._exit`` below ``srv/*/main``);
  - no import-time side effects (module-level bare calls) in a context or bootstrap.

Each checker is also run on an INJECTED violation to prove it has teeth (per the
design's success criterion).
"""

from __future__ import annotations

import ast
import pathlib

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


def test_env_read_only_in_config() -> None:
    offenders: dict[str, list[int]] = {}
    for path in _py_files(exclude={(ROOT / "config.py").resolve()}):
        lines = _env_reads(_parse(path))
        if lines:
            offenders[str(path.relative_to(ROOT))] = lines
    assert not offenders, f"env read outside the config decoder: {offenders}"


def test_only_the_edge_exits() -> None:
    edges = {(ROOT / "srv" / "http" / "main.py").resolve(), (ROOT / "srv" / "cli" / "main.py").resolve()}
    offenders: dict[str, list[int]] = {}
    for path in _py_files(exclude=edges):
        lines = _exits(_parse(path))
        if lines:
            offenders[str(path.relative_to(ROOT))] = lines
    assert not offenders, f"exit below srv/*/main: {offenders}"


def test_no_import_time_side_effects_in_contexts_or_bootstrap() -> None:
    offenders: dict[str, list[int]] = {}
    for pkg in ("campaign", "linkpolicy", "reports", "bootstrap"):
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
