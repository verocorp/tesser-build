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
    ("tesser.srv", "Host"): "host",
    ("tesser.srv", "Port"): "protocol_port",
    ("tesser.srv", "Record"): "protocol_record",
    ("tesser.srv", "Rejection"): "protocol_rejection",
    ("tesser.srv", "Request"): "protocol_request",
    ("tesser.srv", "Response"): "protocol_response",
}

TESSER_DECORATORS: Final[dict[tuple[str, str], str]] = {
    ("tesser.domain", "function"): "function",
    ("tesser.application", "function"): "function",
    ("tesser.adapters", "function"): "function",
    ("tesser.context", "function"): "function",
    ("tesser.srv", "function"): "function",
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
    "host": "a host",
    "protocol_port": "a protocol port",
    "protocol_record": "a protocol record",
    "protocol_rejection": "a protocol rejection",
    "protocol_request": "a protocol request record",
    "protocol_response": "a protocol response record",
}

SRV_KINDS: Final[frozenset[str]] = frozenset(
    block for (package, _), block in TESSER_BASE_BLOCKS.items() if package == "tesser.srv"
)

PROTOCOL_KINDS: Final[frozenset[str]] = SRV_KINDS - frozenset({"host"})

PROTOCOL_PACKAGE: Final[str] = "protocol"

TESSER: Final[str] = "tesser"

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

TESTS_ROLE: Final[str] = "tests"

# `eval_` is the one path-visible special category: a sampled test that calls a
# real model, so it is neither free nor deterministic and CI selects it by name.
# A gateway is its ONLY home. Dropping context-tier evals was safe rather than
# free — the argument for a through-the-service eval was closing the
# input-assembly drift gap, and that gap is closed structurally only while
# schema and prompt assembly stay single-sourced at the edge. If anyone ever
# hand-builds a prompt inside an eval, the tier deleted here was the safety net.
EVAL_PREFIX: Final[str] = "eval_"

EVAL_HOME: Final[str] = "gateways"

# A test's tier is its PLACEMENT, and a sibling test may import what its
# SUBJECT may import, plus the subject itself. The ladder (Chris, 2026-08-09):
# each layer imports and fakes exactly one layer down — srv fakes handlers,
# handlers fake the client, an application service fakes the gateways and repos
# through the ports application itself defines, and gateways/repos fake
# nothing (their correctness is meaningless without the real counterpart).
#
# So the rows are DERIVED from the production import matrix, not hand-written:
# a looser test row than the production row for the same layer licenses
# reach-through the architecture forbids. The one deliberate divergence is
# handlers: SAME_CONTEXT_IMPORTS["adapters"] admits application because
# GATEWAYS need it (parts in their signatures); a handler's production imports
# are client only (the handler carve-out), so its test row is too.
#
# TEST_TIER_HOME names the subject's own role — importing your subject is the
# self-reference every production role has implicitly. The subrole pins
# adapters tests to their own kind: a handler test may not reach gateways.
TEST_TIER_HOME: Final[dict[str, tuple[str, str | None]]] = {
    "domain": ("domain", None),
    "application": ("application", None),
    "handlers": ("adapters", "handlers"),
    "gateways": ("adapters", "gateways"),
}

TEST_TIER_REACH: Final[dict[str, tuple[str, ...]]] = {
    "domain": SAME_CONTEXT_IMPORTS["domain"],
    "application": SAME_CONTEXT_IMPORTS["application"],
    "handlers": ("client",),
    "gateways": SAME_CONTEXT_IMPORTS["adapters"],
    TESTS_ROLE: ROLES,
}

# Which tiers may reach a neighbouring context, and through what.
#
# The context tier needs the neighbour's APPLICATION, not just its client. The
# sanctioned cross-context test wires the REAL neighbour service with the
# neighbour's own ports faked — NoteGateway(NoteService(DroppedNotes())) — which
# needs the service class and its port protocol, both of which live in
# application. A clients-only row would ban that and force a hand-written fake
# client instead, reintroducing the drift the pattern exists to remove: nothing
# proves a fake client still matches the real service.
#
# The gateway tier gets the neighbour's client because production gateways
# already may ("a context reaches another context only through its client, and
# only from gateways and wiring") — a gateway's sibling test has to construct
# what the gateway takes.
TEST_TIER_FOREIGN: Final[dict[str, tuple[str, ...]]] = {
    "gateways": ("client",),
    TESTS_ROLE: ("application", "client"),
}

# The srv tier: a router/host test fakes handlers, so it reaches a context
# only through adapters.handlers — the same door production srv gets ("a host
# reaches a context only through its handlers").
SRV_TIER: Final[str] = "srv"

PRIMITIVES: Final[frozenset[str]] = frozenset({"str", "int", "float", "bool"})

TOOLING_MODULES: Final[frozenset[str]] = frozenset({"rules"})

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


class ImportEdge(ts.ValueObject):

    _target: str
    _lineno: int
    _member_form: bool
    _aliased: bool

    def __init__(self, target: str, lineno: int, member_form: bool, aliased: bool) -> None:
        if not target:
            raise ValueError("target must be non-empty")
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_lineno", lineno)
        object.__setattr__(self, "_member_form", member_form)
        object.__setattr__(self, "_aliased", aliased)

    def target(self) -> str:
        return self._target

    def lineno(self) -> int:
        return self._lineno

    def member_form(self) -> bool:
        return self._member_form

    def aliased(self) -> bool:
        return self._aliased


class TesserImport(ts.ValueObject):

    _target: str
    _lineno: int
    _as_ts: bool
    _from_form: bool

    def __init__(self, target: str, lineno: int, as_ts: bool, from_form: bool) -> None:
        if not target:
            raise ValueError("target must be non-empty")
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_lineno", lineno)
        object.__setattr__(self, "_as_ts", as_ts)
        object.__setattr__(self, "_from_form", from_form)

    def target(self) -> str:
        return self._target

    def lineno(self) -> int:
        return self._lineno

    def as_ts(self) -> bool:
        return self._as_ts

    def from_form(self) -> bool:
        return self._from_form


class ModuleSpec(ts.Spec):

    def __init__(self, name: str, source: str, is_package: bool) -> None:
        self.name = name
        self.source = source
        self.is_package = is_package


class Module(ts.Entity):

    def __init__(self, spec: ModuleSpec) -> None:
        if not spec.name:
            raise ValueError("module name must be non-empty")
        try:
            tree = ast.parse(spec.source)
        except SyntaxError as error:
            raise ValueError(f"module {spec.name} does not parse: {error}") from error
        self._name = spec.name
        self._is_package = spec.is_package
        parts = spec.name.split(".")
        self._package: tuple[str, ...] = tuple(parts if spec.is_package else parts[:-1])
        self._body: tuple[ast.stmt, ...] = tuple(tree.body)
        self._package_aliases: dict[str, str] = {}
        self._imported: dict[str, tuple[str, str]] = {}
        self._classes: dict[str, ast.ClassDef] = {}
        edges: list[ImportEdge] = []
        tesser_imports: list[TesserImport] = []
        nested_tesser: list[tuple[str, int]] = []
        broken_relatives: list[tuple[str, int]] = []
        top_level = {
            id(node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == TESSER:
                        if id(node) in top_level:
                            tesser_imports.append(
                                TesserImport(alias.name, node.lineno, alias.asname == "ts", False)
                            )
                        else:
                            nested_tesser.append((alias.name, node.lineno))
                    if id(node) in top_level:
                        self._package_aliases[alias.asname or alias.name] = alias.name
                    edges.append(
                        ImportEdge(alias.name, node.lineno, False, alias.asname is not None)
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.level > len(self._package):
                    dots = "." * node.level
                    broken_relatives.append((dots + (node.module or ""), node.lineno))
                    continue
                base = self._relative_base(node.level)
                if node.module is None:
                    for alias in node.names:
                        target = ".".join(base + (alias.name,))
                        if id(node) in top_level:
                            self._package_aliases[alias.asname or alias.name] = target
                        edges.append(ImportEdge(target, node.lineno, True, False))
                    continue
                target = ".".join(base + (node.module,))
                for alias in node.names:
                    if id(node) in top_level:
                        self._imported[alias.asname or alias.name] = (target, alias.name)
                edges.append(ImportEdge(target, node.lineno, True, False))
                if target.split(".")[0] == TESSER:
                    if id(node) in top_level:
                        tesser_imports.append(TesserImport(target, node.lineno, False, True))
                    else:
                        nested_tesser.append((target, node.lineno))
        functions: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                self._classes[node.name] = node
            elif isinstance(node, ast.FunctionDef):
                functions.add(node.name)
        self._edges: tuple[ImportEdge, ...] = tuple(edges)
        self._tesser_imports: tuple[TesserImport, ...] = tuple(tesser_imports)
        self._nested_tesser: tuple[tuple[str, int], ...] = tuple(nested_tesser)
        self._broken_relatives: tuple[tuple[str, int], ...] = tuple(broken_relatives)
        self._functions: frozenset[str] = frozenset(functions)
        self._class_defs: tuple[ast.ClassDef, ...] = tuple(self._classes.values())
        self._bound_names: tuple[tuple[str, str, str], ...] = tuple(
            (local, target, original) for local, (target, original) in self._imported.items()
        )

    def _relative_base(self, level: int) -> tuple[str, ...]:
        if level == 0:
            return ()
        return self._package[: max(0, len(self._package) - (level - 1))]

    def name(self) -> str:
        return self._name

    def is_package(self) -> bool:
        return self._is_package

    def body(self) -> tuple[ast.stmt, ...]:
        return self._body

    def import_edges(self) -> tuple[ImportEdge, ...]:
        return self._edges

    def tesser_imports(self) -> tuple[TesserImport, ...]:
        return self._tesser_imports

    def nested_tesser_imports(self) -> tuple[tuple[str, int], ...]:
        return self._nested_tesser

    def broken_relative_imports(self) -> tuple[tuple[str, int], ...]:
        return self._broken_relatives

    def function_names(self) -> frozenset[str]:
        return self._functions

    def class_defs(self) -> tuple[ast.ClassDef, ...]:
        return self._class_defs

    def bound_names(self) -> tuple[tuple[str, str, str], ...]:
        return self._bound_names

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

    def __init__(self, sources: tuple[tuple[str, str, bool], ...]) -> None:
        self.sources = sources


class Codebase(ts.AggregateRoot):

    def __init__(self, spec: CodebaseSpec) -> None:
        modules = tuple(
            Module(ModuleSpec(name=name, source=source, is_package=is_package))
            for name, source, is_package in spec.sources
        )
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
        if basename.startswith(EVAL_PREFIX):
            return self._eval_module_violations(module, blocks, contexts)
        if parts[0] in APP_PACKAGES:
            if module.is_package():
                return self._app_init_violations(module)
            body = (
                self._srv_module_violations(module, blocks)
                if parts[0] == "srv"
                else self._bootstrap_module_violations(module)
            )
            return body + self._app_import_violations(module, parts[0], contexts, blocks)
        if parts[0] == "tests":
            return self._tests_package_violations(module)
        if parts[0] == PROTOCOL_PACKAGE:
            if module.is_package():
                return self._protocol_init_violations(module)
            return self._protocol_module_violations(module, blocks, contexts)
        if parts[0] not in contexts:
            return self._homeless_violations(module)
        if len(parts) == 1:
            return self._context_init_violations(module)
        if basename == "__main__":
            return ()
        if len(parts) >= 2 and parts[1] == TESTS_ROLE:
            # The context tier. A context may hold a tests package alongside its
            # five roles: the multi-boundary test constructs adapters and wiring,
            # not just one role, so it needs a home whose implied import scope it
            # does not immediately violate. Its members are test modules, reached
            # by the test branch above; anything else is a finding.
            if module.is_package():
                return self._context_tests_init_violations(module)
            return (
                Violation(
                    f"{module.name()} is neither a test module nor conftest; "
                    "a context tests package holds only test modules and conftest"
                ),
            )
        if len(parts) >= 2 and parts[1] in ROLES:
            if module.is_package():
                return self._role_init_violations(module)
            if len(parts) == 2:
                return (
                    Violation(
                        f"{module.name()} is a role module; a role is a package, never a module"
                    ),
                )
            return self._role_module_violations(module, parts[1], blocks) + self._import_violations(
                module, parts[0], parts[1], contexts, blocks
            )
        return (
            Violation(
                f"{module.name()} is not a context module; "
                "a context holds only domain, application, client, adapters, wiring, and tests modules"
            ),
        )

    def _context_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(f"{module.name()} __init__ declares code at line {stmt.lineno}; a context __init__ is empty")
            for stmt in module.body()
        )

    def _protocol_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(
                f"{module.name()} __init__ declares code at line {stmt.lineno}; a protocol __init__ is empty"
            )
            for stmt in module.body()
        )

    def _homeless_violations(self, module: Module) -> tuple[Violation, ...]:
        if module.name() in TOOLING_MODULES:
            return ()
        return (
            Violation(
                f"{module.name()} belongs to no governed package; "
                "every module belongs to a context, srv, bootstrap, tests, or the protocol package"
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

    def _context_tests_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(
                f"{module.name()} __init__ declares code at line {stmt.lineno}; "
                "a context tests __init__ is empty"
            )
            for stmt in module.body()
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
        for edge in module.import_edges():
            target = edge.target()
            lineno = edge.lineno()
            if not target.startswith(module.name() + "."):
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; "
                        "a role __init__ only re-exports from its own role"
                    )
                )
            found.extend(self._form_violations(module, edge))
        return tuple(found)

    def _app_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(
                f"{module.name()} __init__ declares code at line {stmt.lineno}; "
                "a srv or bootstrap __init__ is empty"
            )
            for stmt in module.body()
        )

    @staticmethod
    def _tesser_import_violations(
        module: Module,
        subject: str,
        package: str,
        only_clause: str,
        once_clause: str,
        absent_clause: str | None,
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        seen_own = False
        seen_any = False
        for imp in module.tesser_imports():
            target = imp.target()
            lineno = imp.lineno()
            seen_any = True
            if target != package:
                found.append(Violation(f"{module.name()}:{lineno} imports {target}; {only_clause}"))
            elif seen_own:
                found.append(
                    Violation(f"{module.name()}:{lineno} imports {target} again; {once_clause}")
                )
            else:
                seen_own = True
                if imp.from_form():
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports names from {target}; {once_clause}"
                        )
                    )
                elif not imp.as_ts():
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target} without the ts alias; "
                            f"{once_clause}"
                        )
                    )
        if absent_clause is not None and not seen_any:
            found.append(Violation(f"{module.name()} never imports {package}; {absent_clause}"))
        return tuple(found)

    def _statement_violations(
        self,
        module: Module,
        subject: str,
        loose_clause: str,
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.ClassDef)):
                continue
            if isinstance(stmt, ast.FunctionDef):
                if not self._declared(module, stmt, "function"):
                    found.append(
                        Violation(
                            f"{module.name()}.{stmt.name}:{stmt.lineno} is an undeclared module function; "
                            f"a {subject} function declares itself with @ts.function"
                        )
                    )
            elif isinstance(stmt, ast.AnnAssign):
                if not self._is_final(stmt.annotation):
                    found.append(
                        Violation(
                            f"{module.name()}:{stmt.lineno} declares a module constant without Final; "
                            f"a {subject} constant is Final"
                        )
                    )
            elif isinstance(stmt, ast.Assign):
                found.append(
                    Violation(
                        f"{module.name()}:{stmt.lineno} declares a module constant without Final; "
                        f"a {subject} constant is Final"
                    )
                )
            else:
                found.append(
                    Violation(
                        f"{module.name()}:{stmt.lineno} has a loose module-level statement; {loose_clause}"
                    )
                )
        return tuple(found)

    def _bootstrap_module_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(self._stray_import_violations(module))
        found.extend(
            self._tesser_import_violations(
                module,
                "bootstrap",
                "tesser.context",
                "a bootstrap module imports only tesser.context",
                "a bootstrap module imports tesser.context exactly once, as ts",
                "a bootstrap module imports tesser.context exactly once, as ts",
            )
        )
        for stmt in module.body():
            if isinstance(stmt, ast.ClassDef):
                found.append(
                    Violation(
                        f"{module.name()}.{stmt.name}:{stmt.lineno} is a class; "
                        "a bootstrap module holds only imports, declared functions, and Final constants"
                    )
                )
        found.extend(
            self._statement_violations(
                module,
                "bootstrap",
                "a bootstrap module holds only imports, declared functions, and Final constants",
            )
        )
        return tuple(found)

    def _srv_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(self._stray_import_violations(module))
        found.extend(
            self._tesser_import_violations(
                module,
                "srv",
                "tesser.srv",
                "a srv module imports only tesser.srv",
                "a srv module imports tesser.srv exactly once, as ts",
                "a srv module imports tesser.srv exactly once, as ts",
            )
        )
        for stmt in module.body():
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}:{stmt.lineno}"
                if block is None:
                    found.append(Violation(f"{where} declares no ts.* base; a srv class declares its block"))
                elif block != "host":
                    found.append(
                        Violation(f"{where} is {KIND_NAME[block]}; only a host class lives in a srv module")
                    )
        found.extend(
            self._statement_violations(
                module,
                "srv",
                "a srv module holds only imports, declared classes and functions, and Final constants",
            )
        )
        return tuple(found)

    def _protocol_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(self._stray_import_violations(module))
        found.extend(
            self._tesser_import_violations(
                module,
                "protocol",
                "tesser.srv",
                "a protocol module imports only tesser.srv",
                "a protocol module imports tesser.srv exactly once, as ts",
                "a protocol module imports tesser.srv exactly once, as ts",
            )
        )
        for edge in module.import_edges():
            target = edge.target()
            lineno = edge.lineno()
            head = target.split(".")[0]
            if head in contexts:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; "
                        "a protocol module is context-generic and imports no context"
                    )
                )
            elif head in APP_PACKAGES:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; "
                        "a protocol module never imports srv or bootstrap"
                    )
                )
        for stmt in module.body():
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}:{stmt.lineno}"
                if block is None:
                    found.append(Violation(f"{where} declares no ts.* base; a protocol class declares its block"))
                elif block not in PROTOCOL_KINDS:
                    found.append(
                        Violation(
                            f"{where} is {KIND_NAME[block]}; only protocol ports, protocol records, "
                            "protocol rejections, protocol requests, and protocol responses live in a protocol module"
                        )
                    )
        found.extend(
            self._statement_violations(
                module,
                "protocol",
                "a protocol module holds only imports, declared classes and functions, and Final constants",
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
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}:{stmt.lineno}"
                if block is None:
                    found.append(Violation(f"{where} declares no ts.* base; every context class declares its block"))
                elif block in SRV_KINDS:
                    found.append(
                        Violation(
                            f"{where} is {KIND_NAME[block]}; "
                            "a host lives in srv and a protocol kind in a protocol module, never a context"
                        )
                    )
                elif KIND_ROLE[block] != role:
                    found.append(
                        Violation(
                            f"{where} is {KIND_NAME[block]}, whose home is {KIND_ROLE[block]}.py; "
                            "a kind lives only in its role module"
                        )
                    )
        found.extend(
            self._statement_violations(
                module,
                "module",
                "a context module holds only imports, classes, declared functions, and Final constants",
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
        found.extend(self._stray_import_violations(module))
        holds_handler = self._holds_kind(module, blocks, "handler")
        holds_gateway = self._holds_kind(module, blocks, "gateway")
        found.extend(
            self._tesser_import_violations(
                module,
                "role",
                ROLE_TESSER_PACKAGE[role],
                "a role module imports only its own tesser package",
                "a role module imports its tesser package exactly once, as ts",
                "a role module imports its tesser package exactly once, as ts",
            )
        )
        for edge in module.import_edges():
            target = edge.target()
            lineno = edge.lineno()
            pieces = target.split(".")
            if pieces[0] == TESSER:
                continue
            elif pieces[0] in contexts:
                tail = pieces[1] if len(pieces) > 1 else ""
                denied: list[Violation] = []
                if pieces[0] == context:
                    if role == "adapters" and tail == "client":
                        if not holds_handler:
                            denied.append(
                                Violation(
                                    f"{module.name()}:{lineno} imports {target}; "
                                    "only a handler imports its own context's client"
                                )
                            )
                    elif tail != role and tail not in SAME_CONTEXT_IMPORTS[role]:
                        denied.append(
                            Violation(
                                f"{module.name()}:{lineno} imports {target}; the same-context matrix is "
                                "a role to itself, application to domain and client, adapters to "
                                "application, wiring to application, adapters, and client"
                            )
                        )
                elif tail != "client" or not (role == "wiring" or (role == "adapters" and holds_gateway)):
                    denied.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target}; a context reaches another context "
                            "only through its client, and only from gateways and wiring"
                        )
                    )
                found.extend(denied)
                if not denied:
                    found.extend(self._form_violations(module, edge))
            elif (
                role in CORE_STDLIB
                and target not in CORE_STDLIB[role]
                and pieces[0] not in CORE_STDLIB[role]
            ):
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
        for edge in module.import_edges():
            target = edge.target()
            lineno = edge.lineno()
            pieces = target.split(".")
            tail = pieces[1] if len(pieces) > 1 else ""
            if pieces[0] in contexts:
                denied: list[Violation] = []
                if package == "srv" and not (
                    tail == "adapters" and self._holds_kind(self._module_named(target), blocks, "handler")
                ):
                    denied.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target}; "
                            "a host reaches a context only through its handlers"
                        )
                    )
                elif package == "bootstrap" and tail not in ("wiring", "client", "adapters"):
                    denied.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target}; bootstrap builds from "
                            "wiring, clients, and adapters, never domain or application"
                        )
                    )
                found.extend(denied)
                if not denied:
                    found.extend(self._form_violations(module, edge))
            elif package == "bootstrap" and pieces[0] == "srv":
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}; the composition root never imports a host"
                    )
                )
        return tuple(found)

    @staticmethod
    def _test_tier(module: Module, contexts: frozenset[str]) -> tuple[str, str] | None:
        """The (context, tier) a test module's PLACEMENT puts it in.

        None for the app tier — a top-level tests package, which is free: what
        it wires is everything, and which counterparts are real on a given run
        is the environment's property, not the tree's.
        """
        parts = module.name().split(".")
        if parts[0] == "srv" and len(parts) >= 2:
            return ("", SRV_TIER)
        if len(parts) < 3 or parts[0] not in contexts:
            return None
        if parts[1] == TESTS_ROLE:
            return (parts[0], TESTS_ROLE)
        if parts[1] not in ROLES:
            return None
        if parts[1] == "adapters":
            # adapters/handlers/test_*.py and adapters/gateways/test_*.py are
            # different tiers: an inbound handler is a total transform testable
            # with no transport, an outbound gateway is meaningless without its
            # real counterpart.
            if len(parts) >= 4 and parts[2] in ("handlers", "gateways"):
                return (parts[0], parts[2])
            return None
        return (parts[0], parts[1])

    def _test_placement_violations(
        self,
        module: Module,
        context: str,
        tier: str,
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        if tier == SRV_TIER:
            for edge in module.import_edges():
                target = edge.target()
                lineno = edge.lineno()
                pieces = target.split(".")
                if pieces[0] not in contexts:
                    continue
                if len(pieces) >= 3 and pieces[1] == "adapters" and pieces[2] == "handlers":
                    continue
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}, but a test placed in "
                        "srv reaches a context only through its handlers; "
                        "a test reaches only what its placement allows"
                    )
                )
            return tuple(found)
        reach = TEST_TIER_REACH[tier]
        foreign = TEST_TIER_FOREIGN.get(tier, ())
        home = TEST_TIER_HOME.get(tier)
        if home is None:
            own_roles = ", ".join(reach)
        elif home[1] is None:
            own_roles = ", ".join((home[0], *reach))
        else:
            own_roles = ", ".join((f"{home[0]}.{home[1]}", *reach))
        foreign_roles = ", ".join(foreign)
        for edge in module.import_edges():
            target = edge.target()
            lineno = edge.lineno()
            pieces = target.split(".")
            if pieces[0] == TESSER or pieces[0] not in contexts:
                continue
            tail = pieces[1] if len(pieces) > 1 else ""
            if pieces[0] == context:
                allowed = tail in reach
                if not allowed and home is not None and tail == home[0]:
                    allowed = home[1] is None or (len(pieces) >= 3 and pieces[2] == home[1])
                if not allowed:
                    found.append(
                        Violation(
                            f"{module.name()}:{lineno} imports {target}, but a test placed in "
                            f"{tier} reaches only {own_roles} of its own context; "
                            "a test reaches only what its placement allows"
                        )
                    )
            elif not foreign:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}, but a test placed in "
                        f"{tier} reaches no neighbouring context; "
                        "a test reaches only what its placement allows"
                    )
                )
            elif tail not in foreign:
                found.append(
                    Violation(
                        f"{module.name()}:{lineno} imports {target}, but a test placed in "
                        f"{tier} reaches only {foreign_roles} of a neighbouring context; "
                        "a test reaches only what its placement allows"
                    )
                )
        return tuple(found)

    def _eval_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        """An eval is a sampled test, and a gateway is its only home.

        Both gateway forms take one: flat beside the gateway
        (gateways/eval_llm.py) and nested under an escalated one
        (gateways/<vendor>/evals/eval_*.py). The eval_ prefix alone carries the
        category, so evals follow the same flat-by-default escalation as
        everything else.

        Contents are the test-module ruleset — an eval holds tests, @ts.helper
        builders, and @ts.fake doubles — and its reach is the gateway tier's,
        because that is where it lives.
        """
        parts = module.name().split(".")
        at_home = (
            len(parts) >= 4
            and parts[0] in contexts
            and parts[1] == "adapters"
            and EVAL_HOME in parts[2:-1]
        )
        if not at_home:
            return (
                Violation(
                    f"{module.name()} is an eval outside a gateway; "
                    "an eval lives only in a gateway, the one place a sampled real-model "
                    "call is honest"
                ),
            )
        # No placement call here: _test_tier already resolves an eval under
        # gateways/ (flat or nested) to the gateways tier, so
        # _test_module_violations applies the row. Adding it again double-reports.
        return self._test_module_violations(module, blocks, contexts)

    def _test_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(self._stray_import_violations(module))
        placement = self._test_tier(module, contexts)
        if placement is not None:
            found.extend(self._test_placement_violations(module, placement[0], placement[1], contexts))
        for edge in module.import_edges():
            if edge.target().split(".")[0] in contexts:
                found.extend(self._form_violations(module, edge))
        found.extend(
            self._tesser_import_violations(
                module,
                "test",
                "tesser.testing",
                "a test module imports only tesser.testing",
                "a test module imports tesser.testing at most once, as ts",
                None,
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
                    blocks.get(key) in ("port", "client", "protocol_port")
                    for key in self._base_keys(module, stmt)
                ):
                    found.append(
                        Violation(
                            f"{where} implements no application port, protocol port, or client; "
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
                for local, target, original in module.bound_names():
                    key = (module.name(), local)
                    if key in blocks:
                        continue
                    source = blocks.get((target, original))
                    if source is not None:
                        blocks[key] = source
                        changed = True
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
        functions = module.function_names()
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
            elif isinstance(callee, ast.Name) and callee.id in functions:
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
    def _stray_import_violations(module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for target, lineno in module.nested_tesser_imports():
            found.append(
                Violation(
                    f"{module.name()}:{lineno} imports {target} inside a function; "
                    "a tesser import is module-level"
                )
            )
        for target, lineno in module.broken_relative_imports():
            found.append(
                Violation(
                    f"{module.name()}:{lineno} imports {target} beyond the package root; "
                    "a relative import resolves inside the tree"
                )
            )
        return tuple(found)

    @staticmethod
    def _form_violations(module: Module, edge: ImportEdge) -> tuple[Violation, ...]:
        target = edge.target()
        lineno = edge.lineno()
        if edge.member_form():
            return (
                Violation(
                    f"{module.name()}:{lineno} imports names from {target}; "
                    "a context module is imported as an aliased module, never its members"
                ),
            )
        if not edge.aliased():
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
        text = ast.unparse(annotation)
        return text in ("Final", "typing.Final") or text.startswith(("Final[", "typing.Final["))

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
