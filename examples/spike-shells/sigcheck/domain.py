import ast
from typing import Final

import tesser.domain as ts

TESSER_BASE_BLOCKS: Final[dict[tuple[str, str], str]] = {
    ("tesser.application", "ApplicationService"): "service",
    ("tesser.application", "Port"): "port",
    ("tesser.application", "Parts"): "parts",
    ("tesser.context", "Request"): "request",
    ("tesser.context", "Response"): "response",
    ("tesser.context", "Client"): "client",
    ("tesser.domain", "AggregateRoot"): "aggregate",
    ("tesser.domain", "Entity"): "entity",
    ("tesser.domain", "ValueObject"): "valueobject",
    ("tesser.domain", "Spec"): "spec",
    ("tesser.adapters", "Repository"): "repository",
    ("tesser.adapters", "Gateway"): "gateway",
    ("tesser.adapters", "Handler"): "handler",
    ("tesser.context", "Wiring"): "wiring",
}

TESSER_DECORATORS: Final[dict[tuple[str, str], str]] = {
    ("tesser.domain", "function"): "function",
    ("tesser.application", "function"): "function",
    ("tesser.adapters", "function"): "function",
    ("tesser.context", "function"): "function",
    ("tesser.testing", "helper"): "helper",
    ("tesser.testing", "fake"): "fake",
}

TS_NAME_BY_BLOCK: Final[dict[str, str]] = {
    "request": "ts.Request",
    "response": "ts.Response",
    "spec": "ts.Spec",
}

ROLES: Final[tuple[str, ...]] = ("domain", "application", "client", "adapters", "wiring")

APP_PACKAGES: Final[tuple[str, ...]] = ("srv", "bootstrap")

KIND_ROLE: Final[dict[str, str]] = {
    "aggregate": "domain",
    "entity": "domain",
    "valueobject": "domain",
    "spec": "domain",
    "service": "application",
    "port": "application",
    "parts": "application",
    "request": "client",
    "response": "client",
    "client": "client",
    "repository": "adapters",
    "gateway": "adapters",
    "handler": "adapters",
    "wiring": "wiring",
}

KIND_NAME: Final[dict[str, str]] = {
    "aggregate": "an aggregate",
    "entity": "an entity",
    "valueobject": "a value object",
    "spec": "a spec",
    "service": "a service",
    "port": "a port",
    "parts": "a parts record",
    "request": "a request DTO",
    "response": "a response DTO",
    "client": "a client",
    "repository": "a repository adapter",
    "gateway": "a gateway adapter",
    "handler": "an inbound handler",
    "wiring": "a wiring assembly",
}

ROLE_TESSER_PACKAGE: Final[dict[str, str]] = {
    "domain": "tesser.domain",
    "application": "tesser.application",
    "client": "tesser.context",
    "adapters": "tesser.adapters",
    "wiring": "tesser.context",
}

SAME_CONTEXT_IMPORTS: Final[dict[str, tuple[str, ...]]] = {
    "domain": (),
    "client": (),
    "application": ("domain", "client"),
    "adapters": ("application",),
    "wiring": ("application", "adapters", "client"),
}

PRIMITIVES: Final[frozenset[str]] = frozenset({"str", "int", "float", "bool"})

TOOLING_MODULES: Final[frozenset[str]] = frozenset({"rules"})

CORE_ROLES: Final[frozenset[str]] = frozenset({"domain", "client", "application"})

CORE_STDLIB: Final[dict[str, frozenset[str]]] = {
    "domain": frozenset(
        {"__future__", "typing", "enum", "decimal", "fractions", "datetime", "math", "re", "ast"}
    ),
    "client": frozenset({"__future__", "typing"}),
    "application": frozenset({"__future__", "typing"}),
}

DOMAIN_BLOCKS: Final[frozenset[str]] = frozenset({"aggregate", "entity", "valueobject"})


class Violation(ts.ValueObject):

    _message: str

    def __init__(self, message: str) -> None:
        if not message:
            raise ValueError("message must be non-empty")
        object.__setattr__(self, "_message", message)

    def __str__(self) -> str:
        return self._message


class ModuleSpec(ts.Spec):

    def __init__(self, name: str, source: str) -> None:
        self.name = name
        self.source = source


class Module(ts.Entity):

    def __init__(self, spec: ModuleSpec) -> None:
        if not spec.name:
            raise ValueError("module name must be non-empty")
        try:
            tree = ast.parse(spec.source)
        except SyntaxError as error:
            raise ValueError(f"module {spec.name} does not parse: {error}") from error
        self._name = spec.name
        self._body: list[ast.stmt] = list(tree.body)
        self._package_aliases: dict[str, str] = {}
        self._imported: dict[str, tuple[str, str]] = {}
        self._classes: dict[str, ast.ClassDef] = {}
        self._edges: list[tuple[str, int, bool, bool]] = []
        self._tesser_imports: list[tuple[str, int, str | None, bool]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._package_aliases[alias.asname or alias.name] = alias.name
                    self._edges.append((alias.name, node.lineno, False, alias.asname is not None))
                    if alias.name.split(".")[0] == "tesser":
                        self._tesser_imports.append((alias.name, node.lineno, alias.asname, False))
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    self._imported[alias.asname or alias.name] = (node.module, alias.name)
                self._edges.append((node.module, node.lineno, True, False))
                if node.module.split(".")[0] == "tesser":
                    self._tesser_imports.append((node.module, node.lineno, None, True))
        self._functions: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                self._classes[node.name] = node
            elif isinstance(node, ast.FunctionDef):
                self._functions.add(node.name)

    def name(self) -> str:
        return self._name

    def body(self) -> tuple[ast.stmt, ...]:
        return tuple(self._body)

    def import_edges(self) -> tuple[tuple[str, int, bool, bool], ...]:
        return tuple(self._edges)

    def tesser_imports(self) -> tuple[tuple[str, int, str | None, bool], ...]:
        return tuple(self._tesser_imports)

    def function_names(self) -> frozenset[str]:
        return frozenset(self._functions)

    def class_defs(self) -> tuple[ast.ClassDef, ...]:
        return tuple(self._classes.values())

    def resolve(self, node: ast.expr) -> tuple[str, str] | None:
        if isinstance(node, ast.Attribute) and isinstance(node.value, (ast.Name, ast.Attribute)):
            package = self._package_aliases.get(ast.unparse(node.value))
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
        modules = tuple(Module(ModuleSpec(name=name, source=source)) for name, source in spec.sources)
        names = [module.name() for module in modules]
        if len(names) != len(set(names)):
            raise ValueError("module names must be unique")
        self._modules = modules

    def violations(self) -> tuple[Violation, ...]:
        blocks = self._classify()
        contexts = self._contexts()
        found: list[Violation] = []
        for module in self._modules:
            found.extend(self._module_violations(module, blocks, contexts))
            for cls in module.class_defs():
                block = blocks.get((module.name(), cls.name))
                if block == "aggregate":
                    found.extend(self._constructor_violations(module, cls, blocks, "an aggregate"))
                elif block == "entity":
                    found.extend(self._constructor_violations(module, cls, blocks, "an entity"))
                elif block == "valueobject":
                    found.extend(self._valueobject_violations(module, cls, blocks))
                elif block == "spec":
                    found.extend(self._spec_violations(module, cls, blocks))
                elif block in ("request", "response"):
                    found.extend(self._dto_violations(module, cls, blocks))
                elif block == "client":
                    found.extend(self._client_violations(module, cls, blocks))
                elif block in ("repository", "gateway", "handler"):
                    found.extend(self._record_signature_violations(module, cls, blocks, "an adapter"))
                elif block == "port":
                    found.extend(self._record_signature_violations(module, cls, blocks, "a port"))
                elif block == "service":
                    found.extend(self._service_violations(module, cls, blocks))
        return tuple(found)

    def _contexts(self) -> frozenset[str]:
        found: set[str] = set()
        for module in self._modules:
            parts = module.name().split(".")
            if len(parts) >= 2 and parts[1] in ROLES:
                found.add(parts[0])
        return frozenset(found)

    def _module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        parts = module.name().split(".")
        basename = parts[-1]
        if basename == "conftest":
            return ()
        if basename.startswith("test_"):
            return self._test_module_violations(module, blocks, contexts)
        if parts[0] in APP_PACKAGES:
            return self._app_module_violations(module) + self._app_import_violations(
                module, parts[0], contexts, blocks
            )
        if parts[0] == "tests":
            return self._tests_package_violations(module)
        if parts[0] not in contexts:
            return self._homeless_violations(module)
        if len(parts) == 1:
            return self._context_init_violations(module)
        if basename == "__main__":
            return ()
        if len(parts) >= 2 and parts[1] in ROLES:
            if any(other.name().startswith(module.name() + ".") for other in self._modules):
                return self._role_init_violations(module)
            return self._role_module_violations(module, parts[1], blocks) + self._import_violations(
                module, parts[0], parts[1], contexts, blocks
            )
        return (
            Violation(
                f"{module.name()} is not a context module; "
                "a context holds only domain, application, client, adapters, and wiring modules"
            ),
        )

    def _context_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(f"{module.name()} __init__ declares code at line {stmt.lineno}; a context __init__ is empty")
            for stmt in module.body()
        )

    def _homeless_violations(self, module: Module) -> tuple[Violation, ...]:
        if module.name() in TOOLING_MODULES:
            return ()
        return (
            Violation(
                f"{module.name()} belongs to no governed package; "
                "every module belongs to a context, srv, bootstrap, or tests"
            ),
        )

    def _tests_package_violations(self, module: Module) -> tuple[Violation, ...]:
        if len(module.name().split(".")) == 1:
            return tuple(
                Violation(
                    f"{module.name()} __init__ declares code at line {stmt.lineno}; "
                    "a tests package holds only test modules and conftest"
                )
                for stmt in module.body()
            )
        return (
            Violation(
                f"{module.name()} is neither a test module nor conftest; "
                "a tests package holds only test modules and conftest"
            ),
        )

    def _role_init_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
                found.append(
                    Violation(
                        f"{module.name()} __init__ declares code at line {stmt.lineno}; "
                        "a role __init__ only re-exports from its own role"
                    )
                )
        for target, lineno, is_member, has_alias in module.import_edges():
            if not target.startswith(module.name() + "."):
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; "
                        "a role __init__ only re-exports from its own role"
                    )
                )
        return tuple(found)

    def _app_module_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        seen_context = False
        for target, lineno, alias, from_form in module.tesser_imports():
            if target != "tesser.context":
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; "
                        "a srv or bootstrap module imports only tesser.context"
                    )
                )
            elif seen_context:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target} again; "
                        "a srv or bootstrap module imports tesser.context exactly once, as ts"
                    )
                )
            else:
                seen_context = True
                if from_form:
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports names from {target}; "
                            "a srv or bootstrap module imports tesser.context exactly once, as ts"
                        )
                    )
                elif alias != "ts":
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target} without the ts alias; "
                            "a srv or bootstrap module imports tesser.context exactly once, as ts"
                        )
                    )
        if not seen_context and module.function_names():
            found.append(
                Violation(
                    f"{module.name()} never imports tesser.context; "
                    "a srv or bootstrap module imports tesser.context exactly once, as ts"
                )
            )
        for stmt in module.body():
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(stmt, ast.FunctionDef):
                if not self._declared(module, stmt, "function"):
                    found.append(
                        Violation(
                            f"{module.name()}.{stmt.name}:{stmt.lineno} is an undeclared module function; "
                            "a srv or bootstrap function declares itself with @ts.function"
                        )
                    )
            elif isinstance(stmt, ast.ClassDef):
                found.append(
                    Violation(
                        f"{module.name()}.{stmt.name}:{stmt.lineno} is a class; "
                        "a srv or bootstrap module holds only imports, declared functions, and Final constants"
                    )
                )
            elif isinstance(stmt, ast.AnnAssign):
                if not self._is_final(stmt.annotation):
                    found.append(
                        Violation(
                            f"{module.name()}:{stmt.lineno} declares a module constant without Final; "
                            "a srv or bootstrap constant is Final"
                        )
                    )
            elif isinstance(stmt, ast.Assign):
                found.append(
                    Violation(
                        f"{module.name()}:{stmt.lineno} declares a module constant without Final; "
                        "a srv or bootstrap constant is Final"
                    )
                )
            else:
                found.append(
                    Violation(
                        f"{module.name()}:{stmt.lineno} has a loose module-level statement; "
                        "a srv or bootstrap module holds only imports, declared functions, and Final constants"
                    )
                )
        return tuple(found)

    def _role_module_violations(
        self,
        module: Module,
        role: str,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}:{stmt.lineno}"
                if block is None:
                    found.append(Violation(f"{where} declares no ts.* base; every context class declares its block"))
                elif KIND_ROLE[block] != role:
                    found.append(
                        Violation(
                            f"{where} is {KIND_NAME[block]}, whose home is {KIND_ROLE[block]}.py; "
                            "a kind lives only in its role module"
                        )
                    )
            elif isinstance(stmt, ast.FunctionDef):
                where = f"{module.name()}.{stmt.name}:{stmt.lineno}"
                if not self._declared(module, stmt, "function"):
                    found.append(
                        Violation(
                            f"{where} is an undeclared module function; "
                            "a module function declares itself with @ts.function"
                        )
                    )
            elif isinstance(stmt, ast.AnnAssign):
                if not self._is_final(stmt.annotation):
                    found.append(
                        Violation(
                            f"{module.name()}:{stmt.lineno} declares a module constant without Final; "
                            "a module constant is Final"
                        )
                    )
            elif isinstance(stmt, ast.Assign):
                found.append(
                    Violation(
                        f"{module.name()}:{stmt.lineno} declares a module constant without Final; "
                        "a module constant is Final"
                    )
                )
            else:
                found.append(
                    Violation(
                        f"{module.name()}:{stmt.lineno} has a loose module-level statement; a context module "
                        "holds only imports, classes, declared functions, and Final constants"
                    )
                )
        if role == "adapters":
            kinds = {
                blocks.get((module.name(), cls.name)) for cls in module.class_defs()
            } & {"handler", "gateway", "repository"}
            if len(kinds) > 1:
                found.append(
                    Violation(f"{module.name()} mixes adapter kinds; an adapters module holds one adapter kind")
                )
        return tuple(found)

    def _import_violations(
        self,
        module: Module,
        context: str,
        role: str,
        contexts: frozenset[str],
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        holds_handler = self._holds_kind(module, blocks, "handler")
        holds_gateway = self._holds_kind(module, blocks, "gateway")
        own_package = ROLE_TESSER_PACKAGE[role]
        seen_own = False
        for target, lineno, alias, from_form in module.tesser_imports():
            if target != own_package:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; "
                        "a role module imports only its own tesser package"
                    )
                )
            elif seen_own:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target} again; "
                        "a role module imports its tesser package exactly once, as ts"
                    )
                )
            else:
                seen_own = True
                if from_form:
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports names from {target}; "
                            "a role module imports its tesser package exactly once, as ts"
                        )
                    )
                elif alias != "ts":
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target} without the ts alias; "
                            "a role module imports its tesser package exactly once, as ts"
                        )
                    )
        if not seen_own and (module.class_defs() or module.function_names()):
            found.append(
                Violation(
                    f"{module.name()} never imports {own_package}; "
                    "a role module imports its tesser package exactly once, as ts"
                )
            )
        for target, lineno, is_member, has_alias in module.import_edges():
            pieces = target.split(".")
            if pieces[0] == "tesser":
                continue
            elif pieces[0] in contexts:
                tail = pieces[1] if len(pieces) > 1 else ""
                before = len(found)
                if pieces[0] == context:
                    if role == "adapters" and tail == "client":
                        if not holds_handler:
                            found.append(
                                Violation(
                                    f"{module.name()}:{lineno} imports {target}; "
                                    "only a handler imports its own context's client"
                                )
                            )
                    elif tail != role and tail not in SAME_CONTEXT_IMPORTS[role]:
                        found.append(
                            Violation(
                                f"{module.name()}:{lineno} imports {target}; the same-context matrix is "
                                "a role to itself, application to domain and client, adapters to "
                                "application, wiring to application, adapters, and client"
                            )
                        )
                elif tail != "client" or not (role == "wiring" or (role == "adapters" and holds_gateway)):
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target}; a context reaches another context "
                            "only through its client, and only from gateways and wiring"
                        )
                    )
                if len(found) == before:
                    found.extend(self._form_violations(module, target, lineno, is_member, has_alias))
            elif role in CORE_ROLES and pieces[0] not in CORE_STDLIB[role]:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; domain, client, and application "
                        "import only their context, their tesser package, and the pure stdlib"
                    )
                )
        return tuple(found)

    def _app_import_violations(
        self,
        module: Module,
        package: str,
        contexts: frozenset[str],
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for target, lineno, is_member, has_alias in module.import_edges():
            pieces = target.split(".")
            tail = pieces[1] if len(pieces) > 1 else ""
            if pieces[0] in contexts:
                before = len(found)
                if package == "srv" and not (
                    tail == "adapters" and self._holds_kind(self._module_named(target), blocks, "handler")
                ):
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target}; "
                            "a host reaches a context only through its handlers"
                        )
                    )
                elif package == "bootstrap" and tail not in ("wiring", "client", "adapters"):
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target}; bootstrap builds from "
                            "wiring, clients, and adapters, never domain or application"
                        )
                    )
                if len(found) == before:
                    found.extend(self._form_violations(module, target, lineno, is_member, has_alias))
            elif package == "bootstrap" and pieces[0] == "srv":
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; the composition root never imports a host"
                    )
                )
        return tuple(found)

    def _test_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for target, lineno, is_member, has_alias in module.import_edges():
            if target.split(".")[0] in contexts:
                found.extend(self._form_violations(module, target, lineno, is_member, has_alias))
        seen_testing = False
        for target, lineno, alias, from_form in module.tesser_imports():
            if target != "tesser.testing":
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; a test module imports only tesser.testing"
                    )
                )
            elif seen_testing:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target} again; "
                        "a test module imports tesser.testing at most once, as ts"
                    )
                )
            else:
                seen_testing = True
                if from_form:
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports names from {target}; "
                            "a test module imports tesser.testing at most once, as ts"
                        )
                    )
                elif alias != "ts":
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target} without the ts alias; "
                            "a test module imports tesser.testing at most once, as ts"
                        )
                    )
        for stmt in module.body():
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(stmt, ast.FunctionDef):
                where = f"{module.name()}.{stmt.name}:{stmt.lineno}"
                if stmt.name.startswith("test_"):
                    continue
                if self._declared(module, stmt, "helper"):
                    found.extend(self._helper_violations(module, where, stmt, blocks))
                    continue
                found.append(
                    Violation(
                        f"{where} is neither a test nor a declared helper; a test module holds "
                        "tests, @ts.helper builders, and @ts.fake doubles"
                    )
                )
            elif isinstance(stmt, ast.ClassDef):
                where = f"{module.name()}.{stmt.name}:{stmt.lineno}"
                if not self._declared(module, stmt, "fake"):
                    found.append(
                        Violation(f"{where} is an undeclared class; a test double declares itself with @ts.fake")
                    )
                elif not any(
                    blocks.get(key) in ("port", "client") for key in self._base_keys(module, stmt)
                ):
                    found.append(
                        Violation(
                            f"{where} implements no ts.Port or ts.Client; "
                            "a fake implements the port or client it doubles"
                        )
                    )
            else:
                found.append(
                    Violation(
                        f"{module.name()}:{stmt.lineno} has a loose module-level statement; "
                        "a test module holds only imports, tests, helpers, and fakes"
                    )
                )
        return tuple(found)

    def _helper_violations(
        self,
        module: Module,
        where: str,
        fn: ast.FunctionDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        params = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
        for arg in params:
            if not self._allowed_annotation(module, arg.annotation, blocks, frozenset()):
                found.append(
                    Violation(
                        f"{where} parameter {arg.arg!r} is not a primitive; "
                        "a helper takes only defaulted primitives"
                    )
                )
        positional = fn.args.posonlyargs + fn.args.args
        undefaulted = positional[: len(positional) - len(fn.args.defaults)]
        missing = [arg for arg in undefaulted] + [
            arg for arg, default in zip(fn.args.kwonlyargs, fn.args.kw_defaults) if default is None
        ]
        for arg in missing:
            found.append(
                Violation(
                    f"{where} parameter {arg.arg!r} has no default; a helper takes only defaulted primitives"
                )
            )
        if self._annotation_block(module, fn.returns, blocks) != "spec":
            found.append(Violation(f"{where} does not return a ts.Spec; a helper builds a spec"))
        for node in ast.walk(fn):
            if isinstance(node, (ast.If, ast.Match, ast.For, ast.While, ast.Try)):
                found.append(Violation(f"{where} has control flow at line {node.lineno}; a helper only constructs"))
        return tuple(found)

    def _service_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        methods = [item for item in cls.body if isinstance(item, ast.FunctionDef)]
        method_names = frozenset(method.name for method in methods)
        for item in methods:
            where = f"{module.name()}.{cls.name}.{item.name}:{item.lineno}"
            found.extend(self._delegation_violations(module, method_names, where, item))
            if item.name == "__init__":
                found.extend(self._dependency_violations(module, where, item, blocks))
                continue
            if item.name.startswith("_"):
                continue
            found.extend(
                self._signature_violations(module, where, item, "request", "response", "a service method", blocks)
            )
            found.extend(self._body_violations(where, item))
        return tuple(found)

    def _dependency_violations(
        self,
        module: Module,
        where: str,
        fn: ast.FunctionDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
            if arg.arg == "self":
                continue
            if self._annotation_block(module, arg.annotation, blocks) != "port":
                found.append(
                    Violation(f"{where} parameter {arg.arg!r} is not a ts.Port; a service depends only on ports")
                )
        return tuple(found)

    def _client_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef) or item.name.startswith("_"):
                continue
            where = f"{module.name()}.{cls.name}.{item.name}:{item.lineno}"
            found.extend(
                self._signature_violations(module, where, item, "request", "response", "a client method", blocks)
            )
        return tuple(found)

    def _record_signature_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
        subject: str,
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            where = f"{module.name()}.{cls.name}.{item.name}:{item.lineno}"
            annotations = [
                arg.annotation for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
            ]
            annotations.append(item.returns)
            for annotation in annotations:
                touched = self._domain_block_in(module, annotation, blocks)
                if touched is not None:
                    found.append(
                        Violation(
                            f"{where} carries {KIND_NAME[touched]} in its signature; "
                            f"{subject} speaks records, never domain objects"
                        )
                    )
        return tuple(found)

    def _valueobject_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        init = self._init_of(cls)
        if init is None:
            return ()
        where = f"{module.name()}.{cls.name}.__init__:{init.lineno}"
        for arg in self._params(init):
            if not self._allowed_annotation(module, arg.annotation, blocks, frozenset({"valueobject"})):
                found.append(
                    Violation(
                        f"{where} parameter {arg.arg!r} is not allowed; "
                        "a value object constructs from primitives and value objects"
                    )
                )
        return tuple(found)

    def _spec_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            where = f"{module.name()}.{cls.name}.{item.name}:{item.lineno}"
            if item.name != "__init__":
                found.append(
                    Violation(f"{where} defines a method on a spec; a spec only carries construction data")
                )
                continue
            for arg in self._params(item):
                if not self._allowed_annotation(module, arg.annotation, blocks, frozenset({"valueobject", "spec"})):
                    found.append(
                        Violation(
                            f"{where} parameter {arg.arg!r} is not allowed; "
                            "a spec field is a primitive, a value object, or a child spec"
                        )
                    )
        return tuple(found)

    def _dto_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            where = f"{module.name()}.{cls.name}.{item.name}:{item.lineno}"
            if item.name != "__init__":
                found.append(Violation(f"{where} defines a method on a DTO; a DTO carries data and nothing else"))
                continue
            for arg in self._params(item):
                if not self._allowed_annotation(module, arg.annotation, blocks, frozenset({"request", "response"})):
                    found.append(
                        Violation(
                            f"{where} parameter {arg.arg!r} is not allowed; "
                            "a DTO field is a primitive or another DTO"
                        )
                    )
        return tuple(found)

    def _constructor_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
        subject: str,
    ) -> tuple[Violation, ...]:
        init = self._init_of(cls)
        if init is None:
            return (
                Violation(
                    f"{module.name()}.{cls.name}:{cls.lineno} defines no __init__; "
                    f"{subject} constructs from exactly one ts.Spec"
                ),
            )
        where = f"{module.name()}.{cls.name}.__init__:{init.lineno}"
        return self._signature_violations(module, where, init, "spec", None, "a domain constructor", blocks)

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
        params = self._params(fn)
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

    @staticmethod
    def _params(fn: ast.FunctionDef) -> list[ast.arg]:
        return [
            arg
            for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
            if arg.arg != "self"
        ]

    @staticmethod
    def _init_of(cls: ast.ClassDef) -> ast.FunctionDef | None:
        return next(
            (
                item
                for item in cls.body
                if isinstance(item, ast.FunctionDef) and item.name == "__init__"
            ),
            None,
        )

    @staticmethod
    def _form_violations(
        module: Module,
        target: str,
        lineno: int,
        is_member: bool,
        has_alias: bool,
    ) -> tuple[Violation, ...]:
        if is_member:
            return (
                Violation(
                    f"{module.name()}:{lineno} imports names from {target}; "
                    "a context module is imported as an aliased module, never its members"
                ),
            )
        if not has_alias:
            return (
                Violation(
                    f"{module.name()}:{lineno} imports {target} without an alias; "
                    "a context module is imported as an aliased module, never its members"
                ),
            )
        return ()

    def _module_named(self, name: str) -> Module | None:
        return next((module for module in self._modules if module.name() == name), None)

    @staticmethod
    def _holds_kind(module: Module | None, blocks: dict[tuple[str, str], str], kind: str) -> bool:
        if module is None:
            return False
        return any(blocks.get((module.name(), cls.name)) == kind for cls in module.class_defs())

    @staticmethod
    def _declared(module: Module, node: ast.ClassDef | ast.FunctionDef, kind: str) -> bool:
        for decorator in node.decorator_list:
            key = module.resolve(decorator)
            if key is not None and TESSER_DECORATORS.get(key) == kind:
                return True
        return False

    @staticmethod
    def _is_final(annotation: ast.expr) -> bool:
        return ast.unparse(annotation).startswith("Final")

    @staticmethod
    def _base_keys(module: Module, cls: ast.ClassDef) -> tuple[tuple[str, str], ...]:
        found: list[tuple[str, str]] = []
        for base in cls.bases:
            key = module.resolve(base)
            if key is not None:
                found.append(key)
        return tuple(found)

    def _domain_block_in(
        self,
        module: Module,
        node: ast.expr | None,
        blocks: dict[tuple[str, str], str],
    ) -> str | None:
        if node is None:
            return None
        for sub in ast.walk(node):
            if isinstance(sub, (ast.Name, ast.Attribute)):
                key = module.resolve(sub)
                if key is not None and blocks.get(key) in DOMAIN_BLOCKS:
                    return blocks[key]
        return None

    def _allowed_annotation(
        self,
        module: Module,
        node: ast.expr | None,
        blocks: dict[tuple[str, str], str],
        allowed_blocks: frozenset[str],
    ) -> bool:
        if node is None:
            return False
        if isinstance(node, ast.Constant):
            return node.value is Ellipsis or node.value is None
        if isinstance(node, ast.Name) and node.id in PRIMITIVES:
            return True
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "tuple":
                elements = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
                return all(
                    self._allowed_annotation(module, element, blocks, allowed_blocks) for element in elements
                )
            return False
        key = module.resolve(node)
        return key is not None and blocks.get(key) in allowed_blocks

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
