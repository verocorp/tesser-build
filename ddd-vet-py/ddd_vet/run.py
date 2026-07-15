"""File discovery, test-scoping, and the run entry points."""

import os

from ddd_vet.checks import check_source
from ddd_vet.finding import Finding

# Directories never worth scanning. ``testdata`` holds intentionally
# non-conforming fixtures (the Go side excludes its ``testdata`` dirs the same
# way), so recursion skips it — point the analyzer at a fixture file directly to
# check it.
_SKIP_DIRS: frozenset[str] = frozenset(
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
    """A file is test code (DDD001-003 are exempt there) when its name is a
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
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def run_paths(paths: list[str]) -> tuple[list[Finding], list[str]]:
    """Check every ``.py`` file under ``paths``.

    Returns (findings, errors) where ``errors`` are human-readable messages for
    files that could not be read or parsed.
    """
    findings: list[Finding] = []
    errors: list[str] = []
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
                findings.extend(run_source(path, source))
            except SyntaxError as e:
                errors.append(f"{path}:{e.lineno}: syntax error: {e.msg}")
    findings.sort(key=lambda f: (f.path, f.line, f.col, f.code))
    return findings, errors
