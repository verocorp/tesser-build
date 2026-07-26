from __future__ import annotations

import ast
import pathlib

from tests.discovery import discovered_contexts

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _parse(path: pathlib.Path) -> ast.Module:  # tessercheck:ignore
    return ast.parse(path.read_text(encoding="utf-8"))


def _import_time_side_effects(tree: ast.Module) -> list[int]:  # tessercheck:ignore
    hits: list[int] = []
    for stmt in tree.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            hits.append(stmt.lineno)
    return hits


_CONFIG_OWNERS = frozenset({"cfg", "config"})


def _is_client_access(node: ast.Attribute, contexts: frozenset[str]) -> bool:  # tessercheck:ignore
    if node.attr not in contexts:
        return False
    return not (isinstance(node.value, ast.Name) and node.value.id in _CONFIG_OWNERS)


def _clients_reached(tree: ast.Module, contexts: frozenset[str]) -> tuple[set[str], list[int]]:  # tessercheck:ignore
    reached: set[str] = set()
    aliases: dict[str, str] = {}
    called: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute):
            if _is_client_access(node.value, contexts):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[target.id] = node.value.attr
        if isinstance(node, ast.Attribute) and _is_client_access(node, contexts):
            reached.add(node.attr)
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if isinstance(owner, ast.Attribute) and _is_client_access(owner, contexts):
            called.append(node.lineno)
        if isinstance(owner, ast.Name) and owner.id in aliases:
            called.append(node.lineno)
    return reached, called


def _host_files(sub: str = "") -> list[pathlib.Path]:  # tessercheck:ignore
    return sorted((ROOT / "srv" / sub).rglob("*.py"))


def test_no_import_time_side_effects_in_contexts_or_bootstrap() -> None:
    offenders: dict[str, list[int]] = {}
    for pkg in (*discovered_contexts(), "bootstrap"):
        for path in (ROOT / pkg).rglob("*.py"):
            lines = _import_time_side_effects(_parse(path))
            if lines:
                offenders[str(path.relative_to(ROOT))] = lines
    assert not offenders, f"import-time side effect: {offenders}"


def test_a_context_a_host_exposes_owns_a_handler() -> None:
    contexts = frozenset(discovered_contexts())
    exposed: set[str] = set()
    for path in _host_files():
        reached, _ = _clients_reached(_parse(path), contexts)
        exposed |= reached
    assert exposed, "no context is reachable from a host — the walk found nothing"
    missing = sorted(ctx for ctx in exposed if not (ROOT / ctx / "adapters" / "handlers").is_dir())
    assert not missing, f"a host exposes these contexts but they own no handler role: {missing}"


def test_a_host_routes_and_never_translates() -> None:
    contexts = frozenset(discovered_contexts())
    offenders: dict[str, list[int]] = {}
    for path in _host_files():
        _, called = _clients_reached(_parse(path), contexts)
        if called:
            offenders[str(path.relative_to(ROOT))] = called
    assert not offenders, f"a host calls a context Client instead of routing to a handler: {offenders}"


def test_handler_routing_teeth() -> None:
    contexts = frozenset({"campaign", "reports"})
    direct = ast.parse("def f(app):\n    return app.reports.links_by_verdict()\n")
    aliased = ast.parse("def f(app):\n    reports = app.reports\n    return reports.links_by_verdict()\n")
    routed = ast.parse("def f(app):\n    return ReportsHandler(app.reports)\n")
    configured = ast.parse("def f(cfg):\n    return cfg.reports\n")
    assert _clients_reached(direct, contexts) == ({"reports"}, [2])
    assert _clients_reached(aliased, contexts) == ({"reports"}, [3])
    assert _clients_reached(routed, contexts) == ({"reports"}, [])
    assert _clients_reached(configured, contexts) == (set(), [])


def test_import_time_side_effect_teeth() -> None:
    assert _import_time_side_effects(ast.parse("configure_logging()\n")) == [1]
    assert _import_time_side_effects(ast.parse("x = configure_logging()\n")) == []
