from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

APP_LEVEL_PACKAGES = frozenset({"bootstrap", "srv", "web", "tests"})


def exposes_client(pkg_dir: pathlib.Path) -> bool:
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
