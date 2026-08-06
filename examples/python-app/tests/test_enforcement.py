from __future__ import annotations

import ast

from tests.discovery import discovered_contexts
from tests.support import ROOT, clients_reached, host_files, import_time_side_effects, parse_module


def test_no_import_time_side_effects_in_contexts_or_bootstrap() -> None:
    offenders: dict[str, list[int]] = {}
    for pkg in (*discovered_contexts(), "bootstrap"):
        for path in (ROOT / pkg).rglob("*.py"):
            lines = import_time_side_effects(parse_module(path))
            if lines:
                offenders[str(path.relative_to(ROOT))] = lines
    assert not offenders, f"import-time side effect: {offenders}"


def test_a_context_a_host_exposes_owns_a_handler() -> None:
    contexts = frozenset(discovered_contexts())
    exposed: set[str] = set()
    for path in host_files():
        reached, _ = clients_reached(parse_module(path), contexts)
        exposed |= reached
    assert exposed, "no context is reachable from a host — the walk found nothing"
    missing = sorted(ctx for ctx in exposed if not (ROOT / ctx / "adapters" / "handlers").is_dir())
    assert not missing, f"a host exposes these contexts but they own no handler role: {missing}"


def test_a_host_routes_and_never_translates() -> None:
    contexts = frozenset(discovered_contexts())
    offenders: dict[str, list[int]] = {}
    for path in host_files():
        _, called = clients_reached(parse_module(path), contexts)
        if called:
            offenders[str(path.relative_to(ROOT))] = called
    assert not offenders, f"a host calls a context Client instead of routing to a handler: {offenders}"


def test_handler_routing_teeth() -> None:
    contexts = frozenset({"campaign", "reports"})
    direct = ast.parse("def f(app):\n    return app.reports.links_by_verdict()\n")
    aliased = ast.parse("def f(app):\n    reports = app.reports\n    return reports.links_by_verdict()\n")
    routed = ast.parse("def f(app):\n    return ReportsHandler(app.reports)\n")
    configured = ast.parse("def f(cfg):\n    return cfg.reports\n")
    assert clients_reached(direct, contexts) == ({"reports"}, [2])
    assert clients_reached(aliased, contexts) == ({"reports"}, [3])
    assert clients_reached(routed, contexts) == ({"reports"}, [])
    assert clients_reached(configured, contexts) == (set(), [])


def test_import_time_side_effect_teeth() -> None:
    assert import_time_side_effects(ast.parse("configure_logging()\n")) == [1]
    assert import_time_side_effects(ast.parse("x = configure_logging()\n")) == []
