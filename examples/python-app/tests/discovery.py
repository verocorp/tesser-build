"""Context discovery + the totality classifier — the classify-then-check move.

A bounded context is ANY root-level package whose ``__init__.py`` exposes a
``Client`` (defined there or re-exported). The shape/enforcement checks loop
over what discovery finds, so a NEW context is checked by construction —
nothing to remember to add to a list. The totality guard makes discovery
fail-safe: every root-level package must classify as a known app-level piece
or a Client-bearing context; anything else is "unclassified" and fails, so a
context that forgot its ``Client`` (the ``reports/`` defect class) cannot hide
from the checks by being invisible to them.

This is the porting seam for the later ddd-vet generalization: the same
whole-tree classify-then-check move as ``ddd_vet/classify.py``, kept pure over
``pathlib``/``ast`` so it lifts out unchanged.
"""

from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The known app-level pieces: every root-level package that is NOT a bounded
# context. (errors/lifecycle are modules, not packages, and need no entry.)
APP_LEVEL_PACKAGES = frozenset({"bootstrap", "srv", "tests"})


def exposes_client(pkg_dir: pathlib.Path) -> bool:
    """The discovery key: does the package's top level expose a ``Client``?"""
    init = pkg_dir / "__init__.py"
    if not init.is_file():
        return False
    tree = ast.parse(init.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if any((alias.asname or alias.name) == "Client" for alias in node.names):
                return True
        if isinstance(node, ast.ClassDef) and node.name == "Client":
            return True
    return False


def classify(root: pathlib.Path) -> tuple[list[str], list[str]]:
    """Classify every root-level package dir: ``(contexts, unclassified)``.

    App-level pieces are recognized by name; a context by its ``Client``;
    everything else lands in ``unclassified`` — the totality guard asserts
    that bucket is empty."""
    contexts: list[str] = []
    unclassified: list[str] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name.startswith(".") or path.name == "__pycache__":
            continue
        if path.name in APP_LEVEL_PACKAGES:
            continue
        if exposes_client(path):
            contexts.append(path.name)
        else:
            unclassified.append(path.name)
    return contexts, unclassified


def discovered_contexts() -> list[str]:
    contexts, _ = classify(ROOT)
    return contexts
