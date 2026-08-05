import ast

import tesser.domain as ts

TESSER_BASE_BLOCKS: dict[tuple[str, str], str] = {
    ("tesser.application", "ApplicationService"): "service",
    ("tesser.context", "Request"): "request",
    ("tesser.context", "Response"): "response",
    ("tesser.domain", "AggregateRoot"): "aggregate",
    ("tesser.domain", "Spec"): "spec",
}

TS_NAME_BY_BLOCK: dict[str, str] = {
    "request": "ts.Request",
    "response": "ts.Response",
    "spec": "ts.Spec",
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
        self._functions: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                self._classes[node.name] = node
            elif isinstance(node, ast.FunctionDef):
                self._functions.add(node.name)

    def name(self) -> str:
        return self._name

    def function_names(self) -> frozenset[str]:
        return frozenset(self._functions)

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
        blocks = self._classify()
        found: list[Violation] = []
        for module in self._modules:
            for cls in module.class_defs():
                block = blocks.get((module.name(), cls.name))
                if block == "aggregate":
                    found.extend(self._constructor_violations(module, cls, blocks))
                if block != "service":
                    continue
                methods = [item for item in cls.body if isinstance(item, ast.FunctionDef)]
                method_names = frozenset(method.name for method in methods)
                for item in methods:
                    where = f"{module.name()}.{cls.name}.{item.name}:{item.lineno}"
                    found.extend(self._delegation_violations(module, method_names, where, item))
                    if item.name.startswith("_"):
                        continue
                    found.extend(
                        self._signature_violations(module, where, item, "request", "response", "a service method", blocks)
                    )
                    found.extend(self._body_violations(where, item))
        return tuple(found)

    def _constructor_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
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
        return self._signature_violations(module, where, init, "spec", None, "an aggregate constructor", blocks)

    def _classify(self) -> dict[tuple[str, str], str]:
        blocks = dict(TESSER_BASE_BLOCKS)
        changed = True
        while changed:
            changed = False
            for module in self._modules:
                for cls in module.class_defs():
                    key = (module.name(), cls.name)
                    if key in blocks:
                        continue
                    for base in cls.bases:
                        base_key = module.resolve(base)
                        if base_key is not None and base_key in blocks:
                            blocks[key] = blocks[base_key]
                            changed = True
                            break
        return blocks

    def _signature_violations(
        self,
        module: Module,
        where: str,
        fn: ast.FunctionDef,
        param_block: str,
        return_block: str | None,
        subject: str,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        expected = TS_NAME_BY_BLOCK[param_block]
        found: list[Violation] = []
        params = [
            arg
            for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
            if arg.arg != "self"
        ]
        if fn.args.vararg is not None or fn.args.kwarg is not None:
            found.append(Violation(f"{where} uses *args/**kwargs; {subject} takes exactly one {expected}"))
        if len(params) != 1:
            found.append(Violation(f"{where} takes {len(params)} parameters; {subject} takes exactly one {expected}"))
        for arg in params:
            if self._annotation_block(module, arg.annotation, blocks) != param_block:
                found.append(Violation(f"{where} parameter {arg.arg!r} is not a {expected}; {subject} takes exactly one {expected}"))
        if return_block is not None and self._annotation_block(module, fn.returns, blocks) != return_block:
            found.append(
                Violation(
                    f"{where} does not return a {TS_NAME_BY_BLOCK[return_block]}; "
                    f"{subject} returns a {TS_NAME_BY_BLOCK[return_block]}"
                )
            )
        return tuple(found)

    def _delegation_violations(
        self,
        module: Module,
        method_names: frozenset[str],
        where: str,
        fn: ast.FunctionDef,
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            if (
                isinstance(callee, ast.Attribute)
                and isinstance(callee.value, ast.Name)
                and callee.value.id == "self"
                and callee.attr in method_names
            ):
                found.append(Violation(f"{where} delegates to self.{callee.attr} at line {node.lineno}; a service inlines its logic"))
            elif isinstance(callee, ast.Name) and callee.id in module.function_names():
                found.append(Violation(f"{where} delegates to {callee.id} at line {node.lineno}; a service inlines its logic"))
        return tuple(found)

    def _body_violations(self, where: str, fn: ast.FunctionDef) -> tuple[Violation, ...]:
        found: list[Violation] = []
        first = fn.body[0].lineno
        last = fn.body[-1].end_lineno or fn.body[-1].lineno
        span = last - first + 1
        if span > 10:
            found.append(Violation(f"{where} body spans {span} source lines; a service method body is at most 10 source lines"))
        for node in ast.walk(fn):
            if isinstance(node, ast.If):
                if not isinstance(node.test, ast.Call):
                    found.append(Violation(f"{where} if condition at line {node.lineno} is not a single call; a service method satisfies a condition with one domain call"))
                if self._contains_conditional(self._governed_stmts(node)):
                    found.append(Violation(f"{where} nests a conditional at line {node.lineno}; a service method branches one level deep"))
            elif isinstance(node, ast.Match):
                if not isinstance(node.subject, ast.Call):
                    found.append(Violation(f"{where} match subject at line {node.lineno} is not a single call; a service method satisfies a condition with one domain call"))
                if self._contains_conditional([stmt for case in node.cases for stmt in case.body]):
                    found.append(Violation(f"{where} nests a conditional at line {node.lineno}; a service method branches one level deep"))
        return tuple(found)

    @staticmethod
    def _governed_stmts(node: ast.If) -> list[ast.stmt]:
        stmts = list(node.body)
        is_elif_chain = (
            len(node.orelse) == 1
            and isinstance(node.orelse[0], ast.If)
            and node.orelse[0].col_offset == node.col_offset
        )
        if not is_elif_chain:
            stmts.extend(node.orelse)
        return stmts

    @staticmethod
    def _contains_conditional(stmts: list[ast.stmt]) -> bool:
        return any(
            isinstance(sub, (ast.If, ast.Match))
            for stmt in stmts
            for sub in ast.walk(stmt)
        )

    def _annotation_block(
        self,
        module: Module,
        node: ast.expr | None,
        blocks: dict[tuple[str, str], str],
    ) -> str | None:
        if node is None:
            return None
        key = module.resolve(node)
        if key is None:
            return None
        return blocks.get(key)
