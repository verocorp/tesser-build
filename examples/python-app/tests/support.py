from __future__ import annotations  # tesser:debt-file TB041

import ast
import pathlib

import app as app
import campaign.component as campaign_component
import linkpolicy.component as linkpolicy_component
import protocol as protocol
import reports.component as reports_component

ROOT = pathlib.Path(__file__).resolve().parent.parent

CONFIG_OWNERS = frozenset({"cfg", "config"})


def app_config() -> app.AppConfig:
    return app.AppConfig(
        app.Spec(
            campaign=campaign_component.Config(campaign_component.Spec("memory")),
            linkpolicy=linkpolicy_component.Config(linkpolicy_component.Spec("memory")),
            reports=reports_component.Config(reports_component.Spec()),
            http=app.HttpConfig(app.HttpSpec("", 8080)),
        )
    )


def parse_module(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def import_time_side_effects(tree: ast.Module) -> list[int]:
    hits: list[int] = []
    for stmt in tree.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            hits.append(stmt.lineno)
    return hits


def is_client_access(node: ast.Attribute, contexts: frozenset[str]) -> bool:
    if node.attr not in contexts:
        return False
    return not (isinstance(node.value, ast.Name) and node.value.id in CONFIG_OWNERS)


def clients_reached(tree: ast.Module, contexts: frozenset[str]) -> tuple[set[str], list[int]]:
    reached: set[str] = set()
    aliases: dict[str, str] = {}
    called: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute):
            if is_client_access(node.value, contexts):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[target.id] = node.value.attr
        if isinstance(node, ast.Attribute) and is_client_access(node, contexts):
            reached.add(node.attr)
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if isinstance(owner, ast.Attribute) and is_client_access(owner, contexts):
            called.append(node.lineno)
        if isinstance(owner, ast.Name) and owner.id in aliases:
            called.append(node.lineno)
    return reached, called


def host_files(sub: str = "") -> list[pathlib.Path]:
    return sorted((ROOT / "srv" / sub).rglob("*.py"))


class SpyApp:

    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


def route_ok(http_request: protocol.HttpRequest) -> protocol.HttpResponse:
    return protocol.HttpResponse.json(200, {"seen": dict(http_request.path_params)})


def route_other(http_request: protocol.HttpRequest) -> protocol.HttpResponse:
    return protocol.HttpResponse.json(200, {})


ROUTES = (
    protocol.Route("POST", "/campaigns", route_other),
    protocol.Route("GET", "/campaigns/{campaign_id}", route_ok),
    protocol.Route("GET", "/r/{slug}", route_ok),
    protocol.Route("GET", "/reports/links-by-verdict", route_other),
)
