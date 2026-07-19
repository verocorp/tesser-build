"""File discovery, test-scoping, and the run entry points."""

import ast
import os
from collections.abc import Callable

from tessercheck.checks import check_source, check_tree
from tessercheck.classify import classify_trees
from tessercheck.finding import Finding

# Directories never worth scanning. ``testdata`` holds intentionally
# non-conforming fixtures (the Go side excludes its ``testdata`` dirs the same
# way), so recursion skips it — point the analyzer at a fixture file directly to
# check it.
SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".env",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        ".ruff_cache",
        "node_modules",
        "build",
        "dist",
        ".eggs",
        "testdata",
    }
)


def is_test_path(path: str) -> bool:
    """A file is test code (TB001-003 are exempt there) when its name is a
    pytest module or any path component is a test/fixture directory."""
    parts = os.path.normpath(path).split(os.sep)
    if any(p in {"tests", "test", "testdata"} for p in parts):
        return True
    base = os.path.basename(path)
    return base == "conftest.py" or base.startswith("test_") or base.endswith("_test.py")


def run_source(path: str, source: str) -> list[Finding]:
    """Check one in-memory source, deriving test-scoping from ``path``."""
    return check_source(path, source, is_test_path(path))


def _iter_py_files(root: str) -> list[str]:
    if os.path.isfile(root):
        return [root]
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def run_paths(
    paths: list[str],
    is_test: Callable[[str], bool] | None = None,
) -> tuple[list[Finding], list[str]]:
    """Check every ``.py`` file under ``paths`` as one tree.

    Two passes so the classifier sees the *whole* tree: first read+parse every
    file into a shared ``{path: tree}``, then classify once and check each file
    against that one registry. This is what makes cross-file embedding
    (``embeds_entity``, ``is_member``) resolve — a per-file registry cannot see
    that ``Campaign`` owns a ``ShortLink`` defined in another module.

    ``is_test`` overrides the test-scoping predicate (default:
    :func:`is_test_path`). The tree-fixture harness needs this: fixtures live
    under ``testdata/``, which the default predicate treats as test code, so
    the meta-test injects ``lambda _: False`` to check a fixture tree as
    domain code.

    Returns (findings, errors) where ``errors`` are human-readable messages for
    files that could not be read or parsed (those files are excluded from the
    registry and the checks, not fatal to the run).
    """
    scoping = is_test_path if is_test is None else is_test
    errors: list[str] = []
    trees: dict[str, ast.Module] = {}
    sources: dict[str, str] = {}
    seen: set[str] = set()
    for root in paths:
        for path in _iter_py_files(root):
            if path in seen:
                continue
            seen.add(path)
            try:
                with open(path, encoding="utf-8") as fh:
                    source = fh.read()
            except OSError as e:
                errors.append(f"{path}: cannot read: {e}")
                continue
            try:
                trees[path] = ast.parse(source, filename=path)
                sources[path] = source
            except SyntaxError as e:
                errors.append(f"{path}:{e.lineno}: syntax error: {e.msg}")

    # Classify domain code only — test files construct and exercise domain types
    # but are not themselves domain, and a test fixture class must not shadow a
    # domain type in the shared registry.
    registry = classify_trees(
        {path: tree for path, tree in trees.items() if not scoping(path)}
    )

    findings: list[Finding] = []
    for path, tree in trees.items():
        findings.extend(
            check_tree(path, sources[path], tree, scoping(path), registry)
        )
    findings.sort(key=lambda f: (f.path, f.line, f.col, f.code))
    return findings, errors
