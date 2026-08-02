import ast
import sys
from pathlib import Path

SEED_KINDS = {
    ("tesser.application", "ApplicationService"): "service",
    ("tesser.context", "Request"): "request",
    ("tesser.context", "Response"): "response",
}


class _Module:

    def __init__(self, name: str, tree: ast.Module) -> None:
        self.name = name
        self.package_aliases: dict[str, str] = {}
        self.imported: dict[str, tuple[str, str]] = {}
        self.classes: dict[str, ast.ClassDef] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.package_aliases[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    self.imported[alias.asname or alias.name] = (node.module, alias.name)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                self.classes[node.name] = node


def _load(root: Path) -> dict[str, _Module]:
    modules: dict[str, _Module] = {}
    for path in sorted(root.rglob("*.py")):
        parts = list(path.relative_to(root).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            continue
        name = ".".join(parts)
        modules[name] = _Module(name, ast.parse(path.read_text()))
    return modules


def _resolve(mod: _Module, node: ast.expr) -> tuple[str, str] | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        package = mod.package_aliases.get(node.value.id)
        if package is not None:
            return (package, node.attr)
    if isinstance(node, ast.Name):
        if node.id in mod.imported:
            return mod.imported[node.id]
        if node.id in mod.classes:
            return (mod.name, node.id)
    return None


def _classify(modules: dict[str, _Module]) -> dict[tuple[str, str], str]:
    kinds = dict(SEED_KINDS)
    changed = True
    while changed:
        changed = False
        for mod in modules.values():
            for cls in mod.classes.values():
                key = (mod.name, cls.name)
                if key in kinds:
                    continue
                for base in cls.bases:
                    base_key = _resolve(mod, base)
                    if base_key is not None and base_key in kinds:
                        kinds[key] = kinds[base_key]
                        changed = True
                        break
    return kinds


def _annotation_kind(
    mod: _Module,
    node: ast.expr | None,
    kinds: dict[tuple[str, str], str],
) -> str | None:
    if node is None:
        return None
    key = _resolve(mod, node)
    if key is None:
        return None
    return kinds.get(key)


def check(root: Path) -> list[str]:
    modules = _load(root)
    kinds = _classify(modules)
    findings: list[str] = []
    for mod in modules.values():
        for cls in mod.classes.values():
            if kinds.get((mod.name, cls.name)) != "service":
                continue
            for item in cls.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                if item.name.startswith("_"):
                    continue
                where = f"{mod.name}.{cls.name}.{item.name}:{item.lineno}"
                params = [
                    a
                    for a in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                    if a.arg != "self"
                ]
                if item.args.vararg is not None or item.args.kwarg is not None:
                    findings.append(f"{where} uses *args/**kwargs; a service method takes exactly one ts.Request")
                if len(params) != 1:
                    findings.append(f"{where} takes {len(params)} parameters; a service method takes exactly one ts.Request")
                for arg in params:
                    if _annotation_kind(mod, arg.annotation, kinds) != "request":
                        findings.append(f"{where} parameter {arg.arg!r} is not a ts.Request")
                if _annotation_kind(mod, item.returns, kinds) != "response":
                    findings.append(f"{where} does not return a ts.Response")
    return findings


def main() -> int:
    findings = check(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("."))
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
