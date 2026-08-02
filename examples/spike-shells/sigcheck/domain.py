import ast

import tesser.domain as ts

SEED_KINDS: dict[tuple[str, str], str] = {
    ("tesser.application", "ApplicationService"): "service",
    ("tesser.context", "Request"): "request",
    ("tesser.context", "Response"): "response",
    ("tesser.domain", "AggregateRoot"): "aggregate",
    ("tesser.domain", "Spec"): "spec",
}


class Violation(ts.ValueObject):

    _message: str

    def __init__(self, message: str) -> None:
        if not message:
            raise ValueError("message must be non-empty")
        object.__setattr__(self, "_message", message)

    def __str__(self) -> str:
        return self._message


class Module(ts.Entity):

    def __init__(self, name: str, source: str) -> None:
        if not name:
            raise ValueError("module name must be non-empty")
        try:
            tree = ast.parse(source)
        except SyntaxError as error:
            raise ValueError(f"module {name} does not parse: {error}") from error
        self._name = name
        self._package_aliases: dict[str, str] = {}
        self._imported: dict[str, tuple[str, str]] = {}
        self._classes: dict[str, ast.ClassDef] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._package_aliases[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    self._imported[alias.asname or alias.name] = (node.module, alias.name)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                self._classes[node.name] = node

    def name(self) -> str:
        return self._name

    def class_defs(self) -> tuple[ast.ClassDef, ...]:
        return tuple(self._classes.values())

    def resolve(self, node: ast.expr) -> tuple[str, str] | None:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            package = self._package_aliases.get(node.value.id)
            if package is not None:
                return (package, node.attr)
        if isinstance(node, ast.Name):
            if node.id in self._imported:
                return self._imported[node.id]
            if node.id in self._classes:
                return (self._name, node.id)
        return None


class CodebaseSpec(ts.Spec):

    def __init__(self, sources: tuple[tuple[str, str], ...]) -> None:
        self.sources = sources


class Codebase(ts.AggregateRoot):

    def __init__(self, spec: CodebaseSpec) -> None:
        modules = tuple(Module(name, source) for name, source in spec.sources)
        names = [module.name() for module in modules]
        if len(names) != len(set(names)):
            raise ValueError("module names must be unique")
        self._modules = modules

    def violations(self) -> tuple[Violation, ...]:
        kinds = self._classify()
        found: list[Violation] = []
        for module in self._modules:
            for cls in module.class_defs():
                kind = kinds.get((module.name(), cls.name))
                if kind == "aggregate":
                    found.extend(self._constructor_violations(module, cls, kinds))
                if kind != "service":
                    continue
                for item in cls.body:
                    if not isinstance(item, ast.FunctionDef):
                        continue
                    if item.name.startswith("_"):
                        continue
                    found.extend(self._method_violations(module, cls, item, kinds))
        return tuple(found)

    def _constructor_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        kinds: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        init = next(
            (
                item
                for item in cls.body
                if isinstance(item, ast.FunctionDef) and item.name == "__init__"
            ),
            None,
        )
        if init is None:
            return (
                Violation(
                    f"{module.name()}.{cls.name}:{cls.lineno} defines no __init__; "
                    "an aggregate constructs from exactly one ts.Spec"
                ),
            )
        where = f"{module.name()}.{cls.name}.__init__:{init.lineno}"
        found: list[Violation] = []
        params = [
            arg
            for arg in init.args.posonlyargs + init.args.args + init.args.kwonlyargs
            if arg.arg != "self"
        ]
        if init.args.vararg is not None or init.args.kwarg is not None:
            found.append(Violation(f"{where} uses *args/**kwargs; an aggregate constructor takes exactly one ts.Spec"))
        if len(params) != 1:
            found.append(Violation(f"{where} takes {len(params)} parameters; an aggregate constructor takes exactly one ts.Spec"))
        for arg in params:
            if self._annotation_kind(module, arg.annotation, kinds) != "spec":
                found.append(Violation(f"{where} parameter {arg.arg!r} is not a ts.Spec"))
        return tuple(found)

    def _classify(self) -> dict[tuple[str, str], str]:
        kinds = dict(SEED_KINDS)
        changed = True
        while changed:
            changed = False
            for module in self._modules:
                for cls in module.class_defs():
                    key = (module.name(), cls.name)
                    if key in kinds:
                        continue
                    for base in cls.bases:
                        base_key = module.resolve(base)
                        if base_key is not None and base_key in kinds:
                            kinds[key] = kinds[base_key]
                            changed = True
                            break
        return kinds

    def _method_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        item: ast.FunctionDef,
        kinds: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        where = f"{module.name()}.{cls.name}.{item.name}:{item.lineno}"
        found: list[Violation] = []
        params = [
            arg
            for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
            if arg.arg != "self"
        ]
        if item.args.vararg is not None or item.args.kwarg is not None:
            found.append(Violation(f"{where} uses *args/**kwargs; a service method takes exactly one ts.Request"))
        if len(params) != 1:
            found.append(Violation(f"{where} takes {len(params)} parameters; a service method takes exactly one ts.Request"))
        for arg in params:
            if self._annotation_kind(module, arg.annotation, kinds) != "request":
                found.append(Violation(f"{where} parameter {arg.arg!r} is not a ts.Request"))
        if self._annotation_kind(module, item.returns, kinds) != "response":
            found.append(Violation(f"{where} does not return a ts.Response"))
        return tuple(found)

    def _annotation_kind(
        self,
        module: Module,
        node: ast.expr | None,
        kinds: dict[tuple[str, str], str],
    ) -> str | None:
        if node is None:
            return None
        key = module.resolve(node)
        if key is None:
            return None
        return kinds.get(key)
