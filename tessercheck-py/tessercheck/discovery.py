"""Context discovery + the totality guard — the classify-then-check move,
ported from the verified impl (``examples/python-app/tests/discovery.py``).

A bounded context is ANY root-level package whose ``__init__.py`` exposes a
``Client`` (defined there or re-exported) — contexts are *discovered by their
seam*, never declared and never inferred (settled: eng review 2026-07-19,
architecture 3). The totality guard makes discovery fail-safe: every
root-level package must classify as a known app-level piece or a
Client-bearing context; anything else is "unclassified" and fails loudly, so
a context that forgot its ``Client`` (the ``reports/`` defect class) cannot
hide from the checks by being invisible to them.

Narrow declared v1 contract (generalizes the verified impl's hardcoded
layout; assumptions parameterized, not copied):

* Only *direct children* of the app root are classified.
* A directory counts as a root-level package when it contains at least one
  ``.py`` file (recursively). Directories without Python (``docs/``, asset
  dirs) are outside the contract and skipped, as are hidden dirs,
  ``__pycache__``, and the analyzer's standard skip set.
* The app-level set defaults to the template's mandatory top dirs
  (``bootstrap``, ``srv``, ``tests``); a consumer extends it explicitly
  (CLI ``--app-level``) — an extension is a declared fact, not an inference.
* ``__init__.py`` that is missing or unparsable does NOT exempt a package:
  it classifies as unclassified (a namespace package cannot hide).
* An app root with zero discovered contexts is itself a failure — every app
  has at least one Client-bearing context.
"""

import ast
import os
import pathlib
from dataclasses import dataclass

from tessercheck.run import SKIP_DIRS

# The template's mandatory app-level top dirs (skills/tesser-build/map.md
# "App-level, not per-context"), plus the conventional tests dir. Everything
# else at the app root must be a Client-bearing context.
APP_LEVEL_PACKAGES: frozenset[str] = frozenset({"bootstrap", "srv", "tests"})


@dataclass(frozen=True)
class Discovery:
    """One classification of an app root: every root-level package, sorted."""

    contexts: tuple[str, ...]
    unclassified: tuple[str, ...]


def exposes_client(pkg_dir: pathlib.Path) -> bool:
    """The discovery key: does the package's top level expose a ``Client``?

    True for a ``class Client`` defined in ``__init__.py`` or any
    ``from ... import`` that binds the name ``Client`` (directly or via
    ``as Client``) — **as a top-level statement only**. A binding nested in
    a function, class, or conditional (``if False:``, ``if TYPE_CHECKING:``)
    is not a public package attribute at runtime and does not count — a
    dead import cannot smuggle a package past the totality guard. Missing
    or unparsable ``__init__.py`` is False — the caller classifies the
    package as unclassified, never exempt.
    """
    init = pkg_dir / "__init__.py"
    if not init.is_file():
        return False
    try:
        tree = ast.parse(init.read_text(encoding="utf-8"))
    except (SyntaxError, ValueError):
        return False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if any((alias.asname or alias.name) == "Client" for alias in node.names):
                return True
        if isinstance(node, ast.ClassDef) and node.name == "Client":
            return True
    return False


def _is_python_package_dir(path: pathlib.Path) -> bool:
    """Contract: a root-level dir participates when it holds any ``.py`` file.

    Walks with skip-dir *pruning* (never descending into skipped/hidden
    subtrees) and stops at the first hit, so a giant vendored tree inside a
    root-level dir costs nothing. Only components *below* ``path`` are
    judged — an absolute path whose ancestors contain hidden dirs (e.g. a
    checkout under ``.claude/worktrees/``) must not disqualify the tree.
    """
    for _dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        if any(n.endswith(".py") for n in filenames):
            return True
    return False


def classify_root(
    root: pathlib.Path,
    app_level: frozenset[str] = APP_LEVEL_PACKAGES,
) -> Discovery:
    """Classify every root-level package dir of an app root.

    App-level pieces are recognized by name; a context by its ``Client``;
    everything else lands in ``unclassified`` — the totality guard
    (:func:`totality_errors`) asserts that bucket is empty.
    """
    contexts: list[str] = []
    unclassified: list[str] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or path.name.startswith(".") or path.name in SKIP_DIRS:
            continue
        if path.name in app_level:
            continue
        if not _is_python_package_dir(path):
            continue
        if exposes_client(path):
            contexts.append(path.name)
        else:
            unclassified.append(path.name)
    return Discovery(contexts=tuple(contexts), unclassified=tuple(unclassified))


def totality_errors(
    root: pathlib.Path,
    discovery: Discovery,
    app_level: frozenset[str] = APP_LEVEL_PACKAGES,
) -> list[str]:
    """The totality guard, rendered as loud errors naming package and fix.

    Empty when every root-level package classified; otherwise one message per
    unclassified package, plus the no-contexts failure for an app root where
    discovery found nothing to check.
    """
    errors = [
        f"{root / name}: unclassified root-level package — a bounded context "
        f"must expose Client from {name}/__init__.py "
        "(skills/tesser-build/public-interface.md); app-level plumbing must "
        f"be one of {', '.join(sorted(app_level))} (extend with --app-level)"
        for name in discovery.unclassified
    ]
    if not discovery.contexts and not discovery.unclassified:
        errors.append(
            f"{root}: no bounded contexts discovered — every app root has at "
            "least one Client-bearing context (is this the right --app-root?)"
        )
    return errors
