from __future__ import annotations

import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _top_level_imports(pkg_dir: pathlib.Path) -> set[str]:
    names: set[str] = set()
    for path in pkg_dir.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
                names.add(node.module.split(".")[0])
    return names


def test_linkpolicy_never_imports_campaign() -> None:
    assert "campaign" not in _top_level_imports(ROOT / "linkpolicy")


def test_no_peer_imports_reports() -> None:
    assert "reports" not in _top_level_imports(ROOT / "campaign")
    assert "reports" not in _top_level_imports(ROOT / "linkpolicy")


def test_guard_would_catch_a_reverse_import() -> None:
    tree = ast.parse("from campaign import Client\n")
    found = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "campaign" in found
