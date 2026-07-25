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
    for stmt in tree.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            hits.append(stmt.lineno)
    return hits


_CONFIG_OWNERS = frozenset({"cfg", "config"})


def _is_client_access(node: ast.Attribute, contexts: frozenset[str]) -> bool:
    if node.attr not in contexts:
        return False
    return not (isinstance(node.value, ast.Name) and node.value.id in _CONFIG_OWNERS)


def _clients_reached(tree: ast.Module, contexts: frozenset[str]) -> tuple[set[str], list[int]]:
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


def _host_files(sub: str = "") -> list[pathlib.Path]:
    return sorted((ROOT / "srv" / sub).rglob("*.py"))


def _py_files(*, exclude: set[pathlib.Path]) -> list[pathlib.Path]:
    return [
        p
        for p in ROOT.rglob("*.py")
        if p.resolve() not in exclude and "tests" not in p.parts and p.name != "conftest.py"
    ]


def _is_env_edge(rel: pathlib.PurePath) -> bool:
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


def test_the_http_host_routes_and_never_translates() -> None:
    contexts = frozenset(discovered_contexts())
    offenders: dict[str, list[int]] = {}
    for path in _host_files("http"):
        _, called = _clients_reached(_parse(path), contexts)
        if called:
            offenders[str(path.relative_to(ROOT))] = called
    assert not offenders, f"the http host calls a context Client instead of routing to a handler: {offenders}"


def _context_imports(tree: ast.Module, contexts: frozenset[str]) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            module = node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in contexts:
                    hits.append(alias.name)
            continue
        else:
            continue
        if module.split(".")[0] not in contexts:
            continue
        if ".adapters.handlers." in f"{module}.":
            continue
        hits.append(module)
    return hits


def test_the_http_host_imports_only_handlers_from_contexts() -> None:
    contexts = frozenset(discovered_contexts())
    offenders: dict[str, list[str]] = {}
    for path in _host_files("http"):
        hits = _context_imports(_parse(path), contexts)
        if hits:
            offenders[str(path.relative_to(ROOT))] = hits
    assert not offenders, f"the http host reaches past a context's handlers: {offenders}"


def test_host_import_teeth() -> None:
    contexts = frozenset({"campaign", "reports"})
    handler = ast.parse("from campaign.adapters.handlers.http import Handler\n")
    dto = ast.parse("from campaign.client import AddLinkRequest\n")
    service = ast.parse("from campaign.application.service import CampaignService\n")
    whole = ast.parse("import reports\n")
    unrelated = ast.parse("from httpwire import Response\n")
    assert _context_imports(handler, contexts) == []
    assert _context_imports(unrelated, contexts) == []
    assert _context_imports(dto, contexts) == ["campaign.client"]
    assert _context_imports(service, contexts) == ["campaign.application.service"]
    assert _context_imports(whole, contexts) == ["reports"]


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


def test_checkers_flag_injected_violations() -> None:
    assert _env_reads(ast.parse("import os\nx = os.getenv('CAMPAIGN_STORAGE')\n"))
    assert _env_reads(ast.parse("import os\ny = os.environ['X']\n"))
    assert _exits(ast.parse("import sys\ndef f() -> None:\n    sys.exit(1)\n"))
    assert _exits(ast.parse("import os\nos._exit(0)\n"))
    assert _import_time_side_effects(ast.parse("configure_logging()\n"))


def test_env_edge_scoping_teeth() -> None:
    getenv_call = ast.parse("import os\nx = os.getenv('CAMPAIGN_STORAGE')\n")
    environ_read = ast.parse("import os\ny = os.environ['X']\n")
    assert _env_offenders([("campaign/wiring/wire.py", getenv_call)])
    assert _env_offenders([("bootstrap/bootstrap.py", environ_read)])
    assert _env_offenders([("linkpolicy/application/service.py", getenv_call)])
    assert not _env_offenders([("srv/http/main.py", getenv_call)])
    assert not _env_offenders([("srv/cli/main.py", environ_read)])
