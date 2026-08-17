from __future__ import annotations  # tessercheck:ignore-file TB041

import ast
import pathlib

from app.config import Config, HttpConfig, HttpSpec, Spec
from campaign.component.config import Config as CampaignConfig
from campaign.component.config import Spec as CampaignSpec
from protocol.http import HttpRequest, HttpResponse
from linkpolicy.component.config import Config as LinkPolicyConfig
from linkpolicy.component.config import Spec as LinkPolicySpec
from reports.component.config import Config as ReportsConfig
from reports.component.config import Spec as ReportsSpec
from srv.http.router import Route

ROOT = pathlib.Path(__file__).resolve().parent.parent

CONFIG_OWNERS = frozenset({"cfg", "config"})


def app_config() -> Config:
    return Config(
        Spec(
            campaign=CampaignConfig(CampaignSpec("memory")),
            linkpolicy=LinkPolicyConfig(LinkPolicySpec("memory")),
            reports=ReportsConfig(ReportsSpec()),
            http=HttpConfig(HttpSpec("", 8080)),
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


def route_ok(req: HttpRequest) -> HttpResponse:
    return HttpResponse.json(200, {"seen": dict(req.path_params)})


def route_other(req: HttpRequest) -> HttpResponse:
    return HttpResponse.json(200, {})


ROUTES = (
    Route("POST", "/campaigns", route_other),
    Route("GET", "/campaigns/{campaign_id}", route_ok),
    Route("GET", "/r/{slug}", route_ok),
    Route("GET", "/reports/links-by-verdict", route_other),
)
