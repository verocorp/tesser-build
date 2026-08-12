import ast
import builtins
import io
import re
import tokenize
from typing import Final, TypeGuard

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

IGNORE_MARKER: Final[str] = "tessercheck:ignore"

IGNORE_FILE_MARKER: Final[str] = "tessercheck:ignore-file"

CODE_SHAPE: Final[re.Pattern[str]] = re.compile(r"TB[0-9]{3}\Z")

DIRECTIVE: Final[re.Pattern[str]] = re.compile(
    r"^#\s*(!|type:|noqa|tessercheck:ignore|pragma|fmt:|isort:|ruff:)"
)

CATEGORY_MARKER: Final[re.Pattern[str]] = re.compile(r"^#\s*tesser-category:\s*[a-z_]+\s*$")

CODING_DECL: Final[re.Pattern[str]] = re.compile(r"^#.*?coding[:=]\s*[-\w.]+")

MUTABLE_COLLECTIONS: Final[frozenset[str]] = frozenset(
    {
        "list",
        "dict",
        "set",
        "List",
        "Dict",
        "Set",
        "DefaultDict",
        "defaultdict",
        "OrderedDict",
        "Counter",
        "MutableMapping",
        "MutableSequence",
        "MutableSet",
    }
)

MOCK_MODULES: Final[frozenset[str]] = frozenset({"unittest.mock", "mock"})

PATCHER_FIXTURES: Final[frozenset[str]] = frozenset({"monkeypatch", "mocker"})

BUILTIN_NAMES: Final[frozenset[str]] = frozenset(
    name for name in dir(builtins) if not name.startswith("_")
)

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

EVAL_PREFIX: Final[str] = "eval_"

EVAL_HOME: Final[str] = "gateways"

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

TEST_TIER_FOREIGN: Final[dict[str, tuple[str, ...]]] = {
    "gateways": ("client",),
    TESTS_ROLE: ("application", "client"),
}

SRV_TIER: Final[str] = "srv"

PRIMITIVES: Final[frozenset[str]] = frozenset({"str", "int", "float", "bool"})

TOOLING_MODULES: Final[frozenset[str]] = frozenset({"rules"})

CORE_STDLIB: Final[dict[str, frozenset[str]]] = {
    "domain": frozenset(
        {
            "__future__",
            "typing",
            "enum",
            "decimal",
            "fractions",
            "datetime",
            "math",
            "re",
            "ast",
            "io",
            "tokenize",
            "builtins",
        }
    ),
    "client": frozenset({"__future__", "typing"}),
    "application": frozenset({"__future__", "typing"}),
}

DOMAIN_BLOCKS: Final[frozenset[str]] = frozenset({"aggregate", "entity", "valueobject"})

WRAPPABLE_SCALARS: Final[frozenset[str]] = frozenset(
    {"str", "int", "float", "bytes", "Decimal", "date", "datetime", "time"}
)

NON_WRAPPABLE_SCALARS: Final[frozenset[str]] = frozenset({"bool", "complex"})

CANONICAL_EXIT: Final[dict[str, str]] = {
    "str": "__str__",
    "int": "__int__",
    "float": "__float__",
    "bytes": "__bytes__",
    "Decimal": "__str__",
    "date": "__str__",
    "datetime": "__str__",
    "time": "__str__",
}

CONVERSION_DUNDERS: Final[frozenset[str]] = frozenset(
    {"__str__", "__int__", "__float__", "__bytes__"}
)

CANONICAL_HELPER: Final[dict[str, str]] = {
    "str": "canonical_str",
    "int": "canonical_int",
    "float": "canonical_float",
    "bytes": "canonical_bytes",
    "Decimal": "canonical_decimal",
    "datetime": "canonical_datetime",
}

LANGUAGE_FIXED: Final[frozenset[str]] = frozenset(
    {
        "__init__",
        "__hash__",
        "__str__",
        "__repr__",
        "__bool__",
        "__len__",
        "__contains__",
        "__int__",
        "__float__",
        "__bytes__",
        "__index__",
        "__format__",
    }
)

COMPARISON_DUNDERS: Final[frozenset[str]] = frozenset(
    {"__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__"}
)

RETURN_WRAPPERS: Final[frozenset[str]] = frozenset(
    {
        "tuple",
        "Tuple",
        "list",
        "List",
        "set",
        "Set",
        "frozenset",
        "FrozenSet",
        "dict",
        "Dict",
        "Mapping",
        "Sequence",
        "Iterable",
        "Iterator",
        "Collection",
        "Optional",
        "Union",
        "Final",
    }
)

SELF_NAMES: Final[frozenset[str]] = frozenset({"Self", "Never", "NoReturn", "None"})


@ts.function
def canonical_str(value: str) -> str:
    return value


@ts.function
def canonical_int(value: int) -> int:
    return value


class Path(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("path must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class Line(ts.ValueObject):

    _value: int

    def __init__(self, value: int) -> None:
        if value < 1:
            raise ValueError("line must be positive")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return canonical_int(self._value)


class Code(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not CODE_SHAPE.match(value):
            raise ValueError("code must be a TB0xx family code")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class Text(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("text must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class Target(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("target must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class EdgeForm(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("member", "aliased", "bare"):
            raise ValueError("edge form must be member, aliased, or bare")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class ImportForm(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("from", "ts", "alias"):
            raise ValueError("import form must be from, ts, or alias")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class IgnoreScope(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("line", "file"):
            raise ValueError("ignore scope must be line or file")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return canonical_str(self._value)


class Violation(ts.ValueObject):

    _path: Path
    _line: Line
    _code: Code
    _text: Text

    def __init__(self, path: str, line: int, code: str, message: str) -> None:
        object.__setattr__(self, "_path", Path(path))
        object.__setattr__(self, "_line", Line(line))
        object.__setattr__(self, "_code", Code(code))
        object.__setattr__(self, "_text", Text(message))

    def path(self) -> Path:
        return self._path

    def line(self) -> Line:
        return self._line

    def code(self) -> Code:
        return self._code

    def text(self) -> Text:
        return self._text


class Ignore(ts.ValueObject):

    _line: Line
    _codes: tuple[Code, ...]
    _scope: IgnoreScope

    def __init__(self, line: int, codes: tuple[str, ...], file_level: bool) -> None:
        object.__setattr__(self, "_line", Line(line))
        object.__setattr__(self, "_codes", tuple(Code(code) for code in codes))
        object.__setattr__(self, "_scope", IgnoreScope("file" if file_level else "line"))

    def _suppresses(self, violation: Violation) -> bool:
        file_wide = str(self._scope) == "file"
        if file_wide and not self._codes:
            return False
        if self._codes and violation.code() not in self._codes:
            return False
        return file_wide or violation.line() == self._line


class ImportEdge(ts.ValueObject):

    _target: Target
    _lineno: Line
    _form: EdgeForm

    def __init__(self, target: str, lineno: int, member_form: bool, aliased: bool) -> None:
        object.__setattr__(self, "_target", Target(target))
        object.__setattr__(self, "_lineno", Line(lineno))
        object.__setattr__(
            self,
            "_form",
            EdgeForm("member" if member_form else "aliased" if aliased else "bare"),
        )


class TesserImport(ts.ValueObject):

    _target: Target
    _lineno: Line
    _form: ImportForm

    def __init__(self, target: str, lineno: int, as_ts: bool, from_form: bool) -> None:
        object.__setattr__(self, "_target", Target(target))
        object.__setattr__(self, "_lineno", Line(lineno))
        object.__setattr__(
            self,
            "_form",
            ImportForm("from" if from_form else "ts" if as_ts else "alias"),
        )


class Comment(ts.ValueObject):

    _line: Line
    _text: Text

    def __init__(self, line: int, text: str) -> None:
        object.__setattr__(self, "_line", Line(line))
        object.__setattr__(self, "_text", Text(text))


class ModuleSpec(ts.Spec):

    def __init__(self, path: str, name: str, source: str, is_package: bool) -> None:
        self.path = path
        self.name = name
        self.source = source
        self.is_package = is_package


class Module(ts.Entity):

    def __init__(self, spec: ModuleSpec) -> None:
        if not spec.name:
            raise ValueError("module name must be non-empty")
        if not spec.path:
            raise ValueError("module path must be non-empty")
        tree = ast.parse(spec.source)
        self._path = spec.path
        self._comments = self._scan_comments(spec.source)
        self._ignores = self._ignores_from(self._comments)
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

    @staticmethod
    def _scan_comments(source: str) -> tuple[Comment, ...]:
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
        except (tokenize.TokenError, IndentationError):
            return ()
        return tuple(
            Comment(line=token.start[0], text=token.string)
            for token in tokens
            if token.type == tokenize.COMMENT
        )

    @staticmethod
    def _ignores_from(comments: tuple[Comment, ...]) -> tuple[Ignore, ...]:
        found: list[Ignore] = []
        for comment in comments:
            text = str(comment._text).lstrip("#").strip()
            if text.startswith(IGNORE_FILE_MARKER):
                rest = text[len(IGNORE_FILE_MARKER) :]
                file_level = True
            elif text.startswith(IGNORE_MARKER):
                rest = text[len(IGNORE_MARKER) :]
                file_level = False
            else:
                continue
            if rest and rest[0] not in " \t":
                continue
            codes = tuple(part for part in rest.replace(",", " ").split() if part)
            if any(not CODE_SHAPE.match(code) for code in codes):
                continue
            found.append(Ignore(line=int(comment._line), codes=codes, file_level=file_level))
        return tuple(found)

    def _relative_base(self, level: int) -> tuple[str, ...]:
        if level == 0:
            return ()
        return self._package[: max(0, len(self._package) - (level - 1))]

    def name(self) -> str:
        return self._name

    def path(self) -> str:
        return self._path

    def ignores(self) -> tuple[Ignore, ...]:
        return self._ignores

    def comments(self) -> tuple[Comment, ...]:
        return self._comments

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

    def _resolve(self, node: ast.expr) -> tuple[str, str] | None:
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

    def __init__(self, sources: tuple[tuple[str, str, str | None, bool], ...]) -> None:
        self.sources = sources


class Codebase(ts.AggregateRoot):

    def __init__(self, spec: CodebaseSpec) -> None:
        modules: list[Module] = []
        broken: list[Violation] = []
        paths_by_name: dict[str, list[str]] = {}
        for path, name, _, _ in spec.sources:
            paths_by_name.setdefault(name, []).append(path)
        for path, name, source, is_package in spec.sources:
            others = ", ".join(other for other in paths_by_name[name] if other != path)
            if others:
                broken.append(
                    Violation(
                        path,
                        1,
                        "TB043",
                        f"{name} is also defined by {others}; a module has one definition",
                    )
                )
                continue
            if source is None:
                broken.append(
                    Violation(
                        path,
                        1,
                        "TB043",
                        f"{name} could not be read as UTF-8 text; "
                        "every checked module is readable UTF-8 Python",
                    )
                )
                continue
            try:
                modules.append(
                    Module(ModuleSpec(path=path, name=name, source=source, is_package=is_package))
                )
            except SyntaxError as error:
                broken.append(
                    Violation(
                        path,
                        error.lineno or 1,
                        "TB043",
                        f"{name} does not parse ({error.msg}); every checked module parses",
                    )
                )
        self._modules = tuple(modules)
        self._broken = tuple(broken)

    def violations(self) -> tuple[Violation, ...]:
        found = list(self._broken)
        found.extend(self._rule_violations())
        kept: list[Violation] = []
        used: set[tuple[str, Line]] = set()
        by_path = {module.path(): module for module in self._modules}
        for violation in found:
            module = by_path.get(str(violation.path()))
            suppressed = False
            if module is not None:
                for ignore in module.ignores():
                    if ignore._suppresses(violation):
                        used.add((module.path(), ignore._line))
                        suppressed = True
                if suppressed:
                    continue
            kept.append(violation)
        for module in self._modules:
            for ignore in module.ignores():
                if (module.path(), ignore._line) not in used:
                    kept.append(
                        Violation(
                            module.path(),
                            int(ignore._line),
                            "TB090",
                            f"{module.name()} carries an ignore that suppresses nothing; "
                            "an ignore comment suppresses an actual finding",
                        )
                    )
        return tuple(kept)

    def _rule_violations(self) -> tuple[Violation, ...]:
        blocks = self._classify()
        contexts = self._contexts()
        found: list[Violation] = []
        for module in self._modules:
            found.extend(self._universal_violations(module))
            found.extend(self._module_violations(module, blocks, contexts))
            for cls in module.class_defs():
                block = blocks.get((module.name(), cls.name))
                if block == "aggregate":
                    found.extend(self._constructor_violations(module, cls, blocks, "an aggregate"))
                elif block == "entity":
                    found.extend(self._constructor_violations(module, cls, blocks, "an entity"))
                elif block == "valueobject":
                    found.extend(self._valueobject_violations(module, cls, blocks))
                    found.extend(self._vo_field_violations(module, cls))
                if block in DOMAIN_BLOCKS:
                    found.extend(self._shape_norm_violations(module, cls, block, blocks))
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
            if module.is_package():
                return self._context_tests_init_violations(module)
            return (
                Violation(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is neither a test module nor conftest; "
                    "a context tests package holds only test modules and conftest",
                ),
            )
        if len(parts) >= 2 and parts[1] in ROLES:
            if module.is_package():
                return self._role_init_violations(module)
            if len(parts) == 2:
                return (
                    Violation(
                        module.path(),
                        1,
                        "TB041",
                        f"{module.name()} is a role module; a role is a package, never a module",
                    ),
                )
            return self._role_module_violations(module, parts[1], blocks) + self._import_violations(
                module, parts[0], parts[1], contexts, blocks
            )
        return (
            Violation(
                module.path(),
                1,
                "TB041",
                f"{module.name()} is not a context module; "
                "a context holds only domain, application, client, adapters, wiring, and tests modules",
            ),
        )

    def _context_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a context __init__ is empty",
            )
            for stmt in module.body()
        )

    def _protocol_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a protocol __init__ is empty",
            )
            for stmt in module.body()
        )

    def _homeless_violations(self, module: Module) -> tuple[Violation, ...]:
        if module.name() in TOOLING_MODULES:
            return ()
        return (
            Violation(
                module.path(),
                1,
                "TB040",
                f"{module.name()} belongs to no governed package; "
                "every module belongs to a context, srv, bootstrap, tests, or the protocol package",
            ),
        )

    def _tests_package_violations(self, module: Module) -> tuple[Violation, ...]:
        if len(module.name().split(".")) == 1:
            return tuple(
                Violation(
                    module.path(),
                    stmt.lineno,
                    "TB041",
                    f"{module.name()} __init__ declares code; "
                    "a tests package holds only test modules and conftest",
                )
                for stmt in module.body()
            )
        return (
            Violation(
                module.path(),
                1,
                "TB041",
                f"{module.name()} is neither a test module nor conftest; "
                "a tests package holds only test modules and conftest",
            ),
        )

    def _context_tests_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a context tests __init__ is empty",
            )
            for stmt in module.body()
        )

    def _role_init_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
                found.append(
                    Violation(
                        module.path(),
                        stmt.lineno,
                        "TB042",
                        f"{module.name()} __init__ declares code; "
                        "a role __init__ only re-exports from its own role",
                    )
                )
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            if not target.startswith(module.name() + "."):
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB042",
                        f"{module.name()} imports {target}; "
                        "a role __init__ only re-exports from its own role",
                    )
                )
            found.extend(self._form_violations(module, edge))
        return tuple(found)

    def _app_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a srv or bootstrap __init__ is empty",
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
            target = str(imp._target)
            lineno = int(imp._lineno)
            seen_any = True
            if target != package:
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB050",
                        f"{module.name()} imports {target}; {only_clause}",
                    )
                )
            elif seen_own:
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB050",
                        f"{module.name()} imports {target} again; {once_clause}",
                    )
                )
            else:
                seen_own = True
                if str(imp._form) == "from":
                    found.append(
                        Violation(
                            module.path(),
                            lineno,
                            "TB050",
                            f"{module.name()} imports names from {target}; {once_clause}",
                        )
                    )
                elif str(imp._form) == "alias":
                    found.append(
                        Violation(
                            module.path(),
                            lineno,
                            "TB050",
                            f"{module.name()} imports {target} without the ts alias; {once_clause}",
                        )
                    )
        if absent_clause is not None and not seen_any:
            found.append(
                Violation(
                    module.path(),
                    1,
                    "TB050",
                    f"{module.name()} never imports {package}; {absent_clause}",
                )
            )
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
                            module.path(),
                            stmt.lineno,
                            "TB051",
                            f"{module.name()}.{stmt.name} is an undeclared module function; "
                            f"a {subject} function declares itself with @ts.function",
                        )
                    )
            elif isinstance(stmt, ast.AnnAssign):
                if not self._is_final(stmt.annotation):
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB051",
                            f"{module.name()} declares a module constant without Final; "
                            f"a {subject} constant is Final",
                        )
                    )
            elif isinstance(stmt, ast.Assign):
                found.append(
                    Violation(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()} declares a module constant without Final; "
                        f"a {subject} constant is Final",
                    )
                )
            else:
                found.append(
                    Violation(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()} has a loose module-level statement; {loose_clause}",
                    )
                )
        return tuple(found)

    def _universal_violations(self, module: Module) -> tuple[Violation, ...]:
        if module.name() in TOOLING_MODULES:
            return ()
        found: list[Violation] = []
        found.extend(self._comment_violations(module))
        found.extend(self._double_violations(module))
        found.extend(self._shadowing_violations(module))
        found.extend(self._string_equality_violations(module))
        return tuple(found)

    def _comment_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for comment in module.comments():
            if DIRECTIVE.match(str(comment._text)) or CATEGORY_MARKER.match(str(comment._text)):
                continue
            if int(comment._line) <= 2 and CODING_DECL.match(str(comment._text)):
                continue
            found.append(
                Violation(
                    module.path(),
                    int(comment._line),
                    "TB020",
                    f"{module.name()} carries a code comment; code speaks for itself — "
                    "comments, docstrings, and loose strings belong in the doc layer",
                )
            )
        doc_ids: set[int] = set()
        body = module.body()
        if body and self._is_bare_string(body[0]):
            doc_ids.add(id(body[0]))
        for stmt in body:
            for node in ast.walk(stmt):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.body and self._is_bare_string(node.body[0]):
                        doc_ids.add(id(node.body[0]))
        for stmt in body:
            for node in ast.walk(stmt):
                if not self._is_bare_string(node):
                    continue
                kind = "a docstring" if id(node) in doc_ids else "a bare string statement"
                found.append(
                    Violation(
                        module.path(),
                        node.lineno,
                        "TB020",
                        f"{module.name()} carries {kind}; code speaks for itself — "
                        "comments, docstrings, and loose strings belong in the doc layer",
                    )
                )
        return tuple(found)

    def _double_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            for node in ast.walk(stmt):
                if isinstance(node, ast.ImportFrom):
                    target = node.module or ""
                    if self._is_mock_module(target) or (
                        target == "unittest" and any(alias.name == "mock" for alias in node.names)
                    ):
                        found.append(
                            Violation(
                                module.path(),
                                node.lineno,
                                "TB030",
                                f"{module.name()} imports a mocking library; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            )
                        )
                    elif target in ("pytest", "_pytest.monkeypatch") and any(
                        alias.name == "MonkeyPatch" for alias in node.names
                    ):
                        found.append(
                            Violation(
                                module.path(),
                                node.lineno,
                                "TB030",
                                f"{module.name()} reaches for pytest MonkeyPatch; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            )
                        )
                elif isinstance(node, ast.Import):
                    if any(self._is_mock_module(alias.name) for alias in node.names):
                        found.append(
                            Violation(
                                module.path(),
                                node.lineno,
                                "TB030",
                                f"{module.name()} imports a mocking library; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            )
                        )
                elif isinstance(node, ast.Attribute):
                    if (
                        node.attr == "mock"
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "unittest"
                    ):
                        found.append(
                            Violation(
                                module.path(),
                                node.lineno,
                                "TB030",
                                f"{module.name()} imports a mocking library; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            )
                        )
                    elif (
                        node.attr == "MonkeyPatch"
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "pytest"
                    ):
                        found.append(
                            Violation(
                                module.path(),
                                node.lineno,
                                "TB030",
                                f"{module.name()} reaches for pytest MonkeyPatch; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            )
                        )
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not self._pytest_shaped(node):
                        continue
                    args = node.args
                    for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                        if arg.arg in PATCHER_FIXTURES:
                            found.append(
                                Violation(
                                    module.path(),
                                    arg.lineno,
                                    "TB030",
                                    f"{module.name()}.{node.name} takes the {arg.arg} fixture; "
                                    "a test double is a hand-written fake, never a mocking "
                                    "library or a runtime patcher",
                                )
                            )
        return tuple(found)

    def _shadowing_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        scopes: list[tuple[ast.AST | None, list[ast.AST]]] = [
            (None, [stmt for stmt in module.body()])
        ]
        for stmt in module.body():
            for node in ast.walk(stmt):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    scopes.append((node, list(node.body)))
                elif isinstance(node, ast.Lambda):
                    scopes.append((node, [node.body]))
        for holder, roots in scopes:
            items = self._scope_items(roots)
            bound = self._shadow_bound(holder, items)
            if not bound:
                continue
            for child in items:
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id in bound
                ):
                    found.append(
                        Violation(
                            module.path(),
                            child.lineno,
                            "TB033",
                            f"{module.name()} binds {child.func.id} and calls it in the same "
                            "scope; a shadowed builtin is never called — rename the binding",
                        )
                    )
        return tuple(found)

    def _string_equality_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            for node in ast.walk(stmt):
                if (
                    isinstance(node, ast.Compare)
                    and len(node.ops) == 1
                    and isinstance(node.ops[0], ast.Eq)
                    and self._is_str_call(node.left)
                    and self._is_str_call(node.comparators[0])
                ):
                    found.append(
                        Violation(
                            module.path(),
                            node.lineno,
                            "TB004",
                            f"{module.name()} equates two str() calls; compare value objects "
                            "by value, never by their string form",
                        )
                    )
        return tuple(found)

    def _vo_field_violations(self, module: Module, cls: ast.ClassDef) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in cls.body:
            if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
                continue
            if self._annotation_head(stmt.annotation) in MUTABLE_COLLECTIONS:
                field = stmt.target.id
                found.append(
                    Violation(
                        module.path(),
                        stmt.lineno,
                        "TB002",
                        f"{module.name()}.{cls.name} field {field} is a mutable collection; "
                        "a value object's field is hashable — a tuple or frozenset, never "
                        "a mutable collection",
                    )
                )
        return tuple(found)

    def _shape_norm_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        block: str,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        fields = self._declared_fields(cls)
        leaf = self._leaf_scalar(fields)
        if block == "valueobject":
            found.extend(self._exposure_violations(module, cls, fields))
            found.extend(self._composition_violations(module, cls, fields, leaf))
            found.extend(self._door_violations(module, cls))
            found.extend(self._exit_violations(module, cls, leaf))
        else:
            found.extend(self._copy_violations(module, cls, fields))
            found.extend(self._held_root_violations(module, cls, fields, blocks))
            found.extend(self._structured_exit_violations(module, cls))
        found.extend(self._domain_return_violations(module, cls, blocks))
        return tuple(found)

    def _exposure_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        fields: list[tuple[str, ast.expr, int]],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        by_name = {name: ann for name, ann, _ in fields}
        for field, ann, lineno in fields:
            if field.startswith("_"):
                continue
            if self._annotation_scalar_names(ann) & (WRAPPABLE_SCALARS | NON_WRAPPABLE_SCALARS):
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB010",
                        f"{module.name()}.{cls.name} exposes field {field}; "
                        "a value object hides its representation — a public field belongs on a spec",
                    )
                )
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef) or item.name.startswith("_"):
                continue
            attr = self._bare_field_return(item)
            if attr is None:
                continue
            returned_ann = item.returns if item.returns is not None else by_name.get(attr)
            if returned_ann is None:
                continue
            if self._annotation_scalar_names(returned_ann) & (
                WRAPPABLE_SCALARS | NON_WRAPPABLE_SCALARS
            ):
                found.append(
                    Violation(
                        module.path(),
                        item.lineno,
                        "TB010",
                        f"{module.name()}.{cls.name}.{item.name} passes the raw primitive through; "
                        "a value object's accessor returns a value object — "
                        "the canonical exit is the only primitive door",
                    )
                )
        return tuple(found)

    def _composition_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        fields: list[tuple[str, ast.expr, int]],
        leaf: str | None,
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for field, ann, lineno in fields:
            head = self._annotation_head(ann)
            if head in NON_WRAPPABLE_SCALARS:
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB016",
                        f"{module.name()}.{cls.name} field {field} is a {head}; "
                        "bool and complex are not value-object material — "
                        "model the raw value or reach for an enum",
                    )
                )
        if len(fields) >= 2:
            for field, ann, lineno in fields:
                if self._annotation_scalar_names(ann) & WRAPPABLE_SCALARS:
                    found.append(
                        Violation(
                            module.path(),
                            lineno,
                            "TB016",
                            f"{module.name()}.{cls.name} field {field} is a bare primitive; "
                            "a compound backs itself with child value objects",
                        )
                    )
        return tuple(found)

    def _door_violations(self, module: Module, cls: ast.ClassDef) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            decorators = {
                target.id
                for decorator in item.decorator_list
                if isinstance(target := (decorator.func if isinstance(decorator, ast.Call) else decorator), ast.Name)
            }
            if not decorators & {"classmethod", "staticmethod"}:
                continue
            produced: frozenset[str] = frozenset()
            if item.returns is not None:
                produced = frozenset(
                    name for name, _ in self._produced_names(module, item.returns)
                )
            second_door = bool(produced & {cls.name, "Self"})
            if not produced and self._constructs_own_type(item, cls.name):
                second_door = True
            if second_door:
                found.append(
                    Violation(
                        module.path(),
                        item.lineno,
                        "TB017",
                        f"{module.name()}.{cls.name}.{item.name} is a second construction door; "
                        "a value object has one door — its own __init__",
                    )
                )
        return tuple(found)

    @staticmethod
    def _constructs_own_type(fn: ast.FunctionDef, own: str) -> bool:
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            if isinstance(callee, ast.Name) and callee.id in ("cls", own):
                return True
        return False

    def _produced_names(
        self, module: Module, root: ast.expr
    ) -> list[tuple[str, ast.expr]]:
        produced: list[tuple[str, ast.expr]] = []
        stack: list[ast.expr] = [root]
        while stack:
            node = stack.pop()
            if isinstance(node, ast.Subscript):
                head = self._annotation_head(node.value)
                if head in ("type", "Type", "Callable"):
                    continue
                stack.append(node.slice)
                continue
            if isinstance(node, ast.Constant):
                if isinstance(node.value, str):
                    try:
                        parsed = ast.parse(node.value, mode="eval")
                    except SyntaxError:
                        continue
                    if not isinstance(parsed.body, ast.Constant):
                        stack.append(parsed.body)
                continue
            if isinstance(node, ast.Attribute):
                produced.append((node.attr, node))
                continue
            if isinstance(node, ast.Name):
                produced.append((node.id, node))
                continue
            stack.extend(
                child
                for child in ast.iter_child_nodes(node)
                if isinstance(child, ast.expr)
            )
        return produced

    def _exit_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        leaf: str | None,
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        conversions = [
            item
            for item in cls.body
            if isinstance(item, ast.FunctionDef) and item.name in CONVERSION_DUNDERS
        ]
        if leaf is not None and leaf in WRAPPABLE_SCALARS:
            expected = CANONICAL_EXIT[leaf]
            helper = CANONICAL_HELPER.get(leaf)
            for item in conversions:
                if item.name != expected:
                    found.append(
                        Violation(
                            module.path(),
                            item.lineno,
                            "TB015",
                            f"{module.name()}.{cls.name}.{item.name} is a mismatched exit; "
                            "a leaf defines exactly its backing type's conversion dunder",
                        )
                    )
                elif helper is not None and not self._delegates_to(item, helper):
                    found.append(
                        Violation(
                            module.path(),
                            item.lineno,
                            "TB018",
                            f"{module.name()}.{cls.name}.{item.name} hand-rolls its exit; "
                            "a canonical exit is a one-line delegation to its canonical_* policy",
                        )
                    )
            return tuple(found)
        for item in conversions:
            found.append(
                Violation(
                    module.path(),
                    item.lineno,
                    "TB015",
                    f"{module.name()}.{cls.name}.{item.name} is a primitive exit; "
                    "a structured domain object has no primitive exit — "
                    "decompose through leaf components",
                )
            )
        return tuple(found)

    def _structured_exit_violations(
        self, module: Module, cls: ast.ClassDef
    ) -> tuple[Violation, ...]:
        return tuple(
            Violation(
                module.path(),
                item.lineno,
                "TB015",
                f"{module.name()}.{cls.name}.{item.name} is a primitive exit; "
                "a structured domain object has no primitive exit — "
                "decompose through leaf components",
            )
            for item in cls.body
            if isinstance(item, ast.FunctionDef) and item.name in CONVERSION_DUNDERS
        )

    def _copy_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        fields: list[tuple[str, ast.expr, int]],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        by_name = {name: ann for name, ann, _ in fields}
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef) or item.name.startswith("_"):
                continue
            attr = self._bare_field_return(item)
            if attr is None:
                continue
            returned = (
                self._annotation_head(item.returns) if item.returns is not None else None
            )
            if returned is None and attr in by_name:
                returned = self._annotation_head(by_name[attr])
            if returned in MUTABLE_COLLECTIONS:
                found.append(
                    Violation(
                        module.path(),
                        item.lineno,
                        "TB011",
                        f"{module.name()}.{cls.name}.{item.name} hands back its backing collection; "
                        "an accessor returns a defensive copy, never the backing store",
                    )
                )
        return tuple(found)

    def _held_root_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        fields: list[tuple[str, ast.expr, int]],
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for field, ann, lineno in fields:
            for node in ast.walk(ann):
                if not isinstance(node, (ast.Name, ast.Attribute)):
                    continue
                key = module._resolve(node)
                if key is None or key[1] == cls.name:
                    continue
                if blocks.get(key) == "aggregate":
                    found.append(
                        Violation(
                            module.path(),
                            lineno,
                            "TB012",
                            f"{module.name()}.{cls.name} field {field} holds another aggregate root; "
                            "an aggregate is referenced by its ID value object, never held",
                        )
                    )
        return tuple(found)

    def _domain_return_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if item.name in LANGUAGE_FIXED:
                continue
            if item.name.startswith("_") and item.name not in COMPARISON_DUNDERS:
                continue
            if item.returns is None:
                continue
            if isinstance(item.returns, ast.Constant) and item.returns.value is None:
                continue
            if self._bare_field_return(item) is not None:
                continue
            spec_return = False
            offenders: list[str] = []
            for name, node in self._produced_names(module, item.returns):
                if name in RETURN_WRAPPERS or name in SELF_NAMES or name == cls.name:
                    continue
                key = module._resolve(node)
                if key is not None and blocks.get(key) == "spec":
                    spec_return = True
                    continue
                if key is not None and blocks.get(key) in DOMAIN_BLOCKS:
                    continue
                offenders.append(name)
            if spec_return:
                found.append(
                    Violation(
                        module.path(),
                        item.lineno,
                        "TB015",
                        f"{module.name()}.{cls.name}.{item.name} returns a spec; "
                        "a domain object never serializes itself — "
                        "a spec is construction data, not an exit",
                    )
                )
            if offenders:
                named = ", ".join(sorted(set(offenders)))
                found.append(
                    Violation(
                        module.path(),
                        item.lineno,
                        "TB019",
                        f"{module.name()}.{cls.name}.{item.name} returns {named}; "
                        "a domain object's public behavior hands back domain objects — "
                        "the licensed exits are the protocol dunders, the canonical exit, "
                        "and a -> None transition",
                    )
                )
        return tuple(found)

    @staticmethod
    def _declared_fields(cls: ast.ClassDef) -> list[tuple[str, ast.expr, int]]:
        return [
            (stmt.target.id, stmt.annotation, stmt.lineno)
            for stmt in cls.body
            if isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and Codebase._annotation_head(stmt.annotation) != "ClassVar"
        ]

    def _leaf_scalar(self, fields: list[tuple[str, ast.expr, int]]) -> str | None:
        if len(fields) != 1:
            return None
        head = self._annotation_head(fields[0][1])
        if head in WRAPPABLE_SCALARS or head in NON_WRAPPABLE_SCALARS:
            return head
        return None

    def _annotation_scalar_names(
        self, node: ast.expr, keep_all: bool = False
    ) -> frozenset[str]:
        names: set[str] = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name):
                names.add(sub.id)
            elif isinstance(sub, ast.Attribute):
                names.add(sub.attr)
            elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                try:
                    parsed = ast.parse(sub.value, mode="eval")
                except SyntaxError:
                    continue
                if not isinstance(parsed.body, ast.Constant):
                    names |= self._annotation_scalar_names(parsed.body, keep_all=keep_all)
        if keep_all:
            return frozenset(names)
        return frozenset(names - RETURN_WRAPPERS - SELF_NAMES)

    @staticmethod
    def _bare_field_return(fn: ast.FunctionDef) -> str | None:
        if len(fn.body) != 1 or not isinstance(fn.body[0], ast.Return):
            return None
        value = fn.body[0].value
        if (
            isinstance(value, ast.Attribute)
            and isinstance(value.value, ast.Name)
            and value.value.id == "self"
        ):
            return value.attr
        return None

    @staticmethod
    def _delegates_to(fn: ast.FunctionDef, helper: str) -> bool:
        if len(fn.body) != 1 or not isinstance(fn.body[0], ast.Return):
            return False
        value = fn.body[0].value
        if not isinstance(value, ast.Call) or len(value.args) != 1:
            return False
        callee = value.func
        named = (
            callee.id
            if isinstance(callee, ast.Name)
            else callee.attr if isinstance(callee, ast.Attribute) else None
        )
        return (
            named == helper
            and isinstance(value.args[0], ast.Attribute)
            and isinstance(value.args[0].value, ast.Name)
            and value.args[0].value.id == "self"
        )

    @staticmethod
    def _is_bare_string(node: ast.AST) -> TypeGuard[ast.Expr]:
        return (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )

    @staticmethod
    def _is_mock_module(target: str) -> bool:
        return any(
            target == banned or target.startswith(banned + ".") for banned in MOCK_MODULES
        )

    @staticmethod
    def _pytest_shaped(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        if node.name.startswith("test_"):
            return True
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(target, ast.Attribute) and target.attr == "fixture":
                return True
            if isinstance(target, ast.Name) and target.id == "fixture":
                return True
        return False

    @staticmethod
    def _scope_items(roots: list[ast.AST]) -> list[ast.AST]:
        out: list[ast.AST] = []
        stack: list[ast.AST] = list(roots)
        while stack:
            child = stack.pop()
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
            ):
                continue
            out.append(child)
            stack.extend(ast.iter_child_nodes(child))
        return out

    @staticmethod
    def _shadow_bound(holder: ast.AST | None, items: list[ast.AST]) -> frozenset[str]:
        bound: set[str] = set()
        if isinstance(holder, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = holder.args
            for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                if arg.arg in BUILTIN_NAMES:
                    bound.add(arg.arg)
            for extra in (args.vararg, args.kwarg):
                if extra is not None and extra.arg in BUILTIN_NAMES:
                    bound.add(extra.arg)
        elsewhere: set[str] = set()
        for child in items:
            if isinstance(child, (ast.Global, ast.Nonlocal)):
                elsewhere.update(child.names)
            if (
                isinstance(child, ast.ExceptHandler)
                and child.name is not None
                and child.name in BUILTIN_NAMES
            ):
                bound.add(child.name)
        for child in items:
            targets: list[ast.expr] = []
            if isinstance(child, ast.Assign):
                targets = list(child.targets)
            elif isinstance(child, (ast.AnnAssign, ast.AugAssign)):
                targets = [child.target]
            elif isinstance(child, (ast.For, ast.AsyncFor)):
                targets = [child.target]
            elif isinstance(child, ast.NamedExpr):
                targets = [child.target]
            elif isinstance(child, ast.withitem):
                targets = [child.optional_vars] if child.optional_vars else []
            for target in targets:
                for name in ast.walk(target):
                    if (
                        isinstance(name, ast.Name)
                        and isinstance(name.ctx, ast.Store)
                        and name.id in BUILTIN_NAMES
                    ):
                        bound.add(name.id)
        return frozenset(bound - elsewhere)

    @staticmethod
    def _is_str_call(node: ast.expr) -> bool:
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        if isinstance(func, ast.Name) and func.id == "str" and len(node.args) == 1:
            return True
        return isinstance(func, ast.Attribute) and func.attr == "__str__"

    @staticmethod
    def _annotation_head(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Subscript):
            return Codebase._annotation_head(node.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                parsed = ast.parse(node.value, mode="eval")
            except SyntaxError:
                return None
            if isinstance(parsed.body, ast.Constant):
                return None
            return Codebase._annotation_head(parsed.body)
        return None

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
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()}.{stmt.name} is a class; "
                        "a bootstrap module holds only imports, declared functions, and Final constants",
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
                where = f"{module.name()}.{stmt.name}"
                if block is None:
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} declares no ts.* base; a srv class declares its block",
                        )
                    )
                elif block != "host":
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}; only a host class lives in a srv module",
                        )
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
            target = str(edge._target)
            lineno = int(edge._lineno)
            head = target.split(".")[0]
            if head in contexts:
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB064",
                        f"{module.name()} imports {target}; "
                        "a protocol module is context-generic and imports no context",
                    )
                )
            elif head in APP_PACKAGES:
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB064",
                        f"{module.name()} imports {target}; "
                        "a protocol module never imports srv or bootstrap",
                    )
                )
        for stmt in module.body():
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}"
                if block is None:
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} declares no ts.* base; a protocol class declares its block",
                        )
                    )
                elif block not in PROTOCOL_KINDS:
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}; only protocol ports, protocol records, "
                            "protocol rejections, protocol requests, and protocol responses live in a protocol module",
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
                where = f"{module.name()}.{stmt.name}"
                if block is None:
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} declares no ts.* base; every context class declares its block",
                        )
                    )
                elif block in SRV_KINDS:
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}; "
                            "a host lives in srv and a protocol kind in a protocol module, never a context",
                        )
                    )
                elif KIND_ROLE[block] != role:
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}, whose home is {KIND_ROLE[block]}.py; "
                            "a kind lives only in its role module",
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
                    Violation(
                        module.path(),
                        1,
                        "TB052",
                        f"{module.name()} mixes adapter kinds; an adapters module holds one adapter kind",
                    )
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
            target = str(edge._target)
            lineno = int(edge._lineno)
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
                                    module.path(),
                                    lineno,
                                    "TB060",
                                    f"{module.name()} imports {target}; "
                                    "only a handler imports its own context's client",
                                )
                            )
                    elif tail != role and tail not in SAME_CONTEXT_IMPORTS[role]:
                        denied.append(
                            Violation(
                                module.path(),
                                lineno,
                                "TB060",
                                f"{module.name()} imports {target}; the same-context matrix is "
                                "a role to itself, application to domain and client, adapters to "
                                "application, wiring to application, adapters, and client",
                            )
                        )
                elif tail != "client" or not (role == "wiring" or (role == "adapters" and holds_gateway)):
                    denied.append(
                        Violation(
                            module.path(),
                            lineno,
                            "TB061",
                            f"{module.name()} imports {target}; a context reaches another context "
                            "only through its client, and only from gateways and wiring",
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
                        module.path(),
                        lineno,
                        "TB062",
                        f"{module.name()} imports {target}; domain, client, and application "
                        "import only their context, their tesser package, and the pure stdlib",
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
            target = str(edge._target)
            lineno = int(edge._lineno)
            pieces = target.split(".")
            tail = pieces[1] if len(pieces) > 1 else ""
            if pieces[0] in contexts:
                denied: list[Violation] = []
                if package == "srv" and not (
                    tail == "adapters" and self._holds_kind(self._module_named(target), blocks, "handler")
                ):
                    denied.append(
                        Violation(
                            module.path(),
                            lineno,
                            "TB063",
                            f"{module.name()} imports {target}; "
                            "a host reaches a context only through its handlers",
                        )
                    )
                elif package == "bootstrap" and tail not in ("wiring", "client", "adapters"):
                    denied.append(
                        Violation(
                            module.path(),
                            lineno,
                            "TB063",
                            f"{module.name()} imports {target}; bootstrap builds from "
                            "wiring, clients, and adapters, never domain or application",
                        )
                    )
                found.extend(denied)
                if not denied:
                    found.extend(self._form_violations(module, edge))
            elif package == "bootstrap" and pieces[0] == "srv":
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB063",
                        f"{module.name()} imports {target}; the composition root never imports a host",
                    )
                )
        return tuple(found)

    @staticmethod
    def _test_tier(module: Module, contexts: frozenset[str]) -> tuple[str, str] | None:
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
                target = str(edge._target)
                lineno = int(edge._lineno)
                pieces = target.split(".")
                if pieces[0] not in contexts:
                    continue
                if len(pieces) >= 3 and pieces[1] == "adapters" and pieces[2] == "handlers":
                    continue
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        "srv reaches a context only through its handlers; "
                        "a test reaches only what its placement allows",
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
            target = str(edge._target)
            lineno = int(edge._lineno)
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
                            module.path(),
                            lineno,
                            "TB070",
                            f"{module.name()} imports {target}, but a test placed in "
                            f"{tier} reaches only {own_roles} of its own context; "
                            "a test reaches only what its placement allows",
                        )
                    )
            elif not foreign:
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        f"{tier} reaches no neighbouring context; "
                        "a test reaches only what its placement allows",
                    )
                )
            elif tail not in foreign:
                found.append(
                    Violation(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        f"{tier} reaches only {foreign_roles} of a neighbouring context; "
                        "a test reaches only what its placement allows",
                    )
                )
        return tuple(found)

    def _eval_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
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
                    module.path(),
                    1,
                    "TB070",
                    f"{module.name()} is an eval outside a gateway; "
                    "an eval lives only in a gateway, the one place a sampled real-model "
                    "call is honest",
                ),
            )
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
            if str(edge._target).split(".")[0] in contexts:
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
                where = f"{module.name()}.{stmt.name}"
                if stmt.name.startswith("test_"):
                    continue
                if self._declared(module, stmt, "helper"):
                    found.extend(self._helper_violations(module, where, stmt.lineno, stmt, blocks))
                    continue
                found.append(
                    Violation(
                        module.path(),
                        stmt.lineno,
                        "TB071",
                        f"{where} is neither a test nor a declared helper; a test module holds "
                        "tests, @ts.helper builders, and @ts.fake doubles",
                    )
                )
            elif isinstance(stmt, ast.ClassDef):
                where = f"{module.name()}.{stmt.name}"
                if not self._declared(module, stmt, "fake"):
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB072",
                            f"{where} is an undeclared class; a test double declares itself with @ts.fake",
                        )
                    )
                elif not any(
                    blocks.get(key) in ("port", "client", "protocol_port")
                    for key in self._base_keys(module, stmt)
                ):
                    found.append(
                        Violation(
                            module.path(),
                            stmt.lineno,
                            "TB072",
                            f"{where} implements no application port, protocol port, or client; "
                            "a fake implements the port or client it doubles",
                        )
                    )
            else:
                found.append(
                    Violation(
                        module.path(),
                        stmt.lineno,
                        "TB071",
                        f"{module.name()} has a loose module-level statement; "
                        "a test module holds only imports, tests, helpers, and fakes",
                    )
                )
        return tuple(found)

    def _helper_violations(
        self,
        module: Module,
        where: str,
        line: int,
        fn: ast.FunctionDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        params = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
        for arg in params:
            if not self._allowed_annotation(module, arg.annotation, blocks, frozenset()):
                found.append(
                    Violation(
                        module.path(),
                        line,
                        "TB073",
                        f"{where} parameter {arg.arg!r} is not a primitive; "
                        "a helper takes only defaulted primitives",
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
                    module.path(),
                    line,
                    "TB073",
                    f"{where} parameter {arg.arg!r} has no default; "
                    "a helper takes only defaulted primitives",
                )
            )
        if self._annotation_block(module, fn.returns, blocks) != "spec":
            found.append(
                Violation(
                    module.path(),
                    line,
                    "TB073",
                    f"{where} does not return a ts.Spec; a helper builds a spec",
                )
            )
        for node in ast.walk(fn):
            if isinstance(node, (ast.If, ast.Match, ast.For, ast.While, ast.Try)):
                found.append(
                    Violation(
                        module.path(),
                        node.lineno,
                        "TB073",
                        f"{where} has control flow; a helper only constructs",
                    )
                )
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
            where = f"{module.name()}.{cls.name}.{item.name}"
            found.extend(self._delegation_violations(module, method_names, where, item))
            if item.name == "__init__":
                found.extend(self._dependency_violations(module, where, item.lineno, item, blocks))
                continue
            if item.name.startswith("_"):
                continue
            found.extend(
                self._signature_violations(
                    module, where, item.lineno, item, "request", "response", "a service method", "TB081", blocks
                )
            )
            found.extend(self._body_violations(module, where, item))
        return tuple(found)

    def _dependency_violations(
        self,
        module: Module,
        where: str,
        line: int,
        fn: ast.FunctionDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
            if arg.arg == "self":
                continue
            if self._annotation_block(module, arg.annotation, blocks) != "port":
                found.append(
                    Violation(
                        module.path(),
                        line,
                        "TB081",
                        f"{where} parameter {arg.arg!r} is not a ts.Port; "
                        "a service depends only on ports",
                    )
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
            where = f"{module.name()}.{cls.name}.{item.name}"
            found.extend(
                self._signature_violations(
                    module, where, item.lineno, item, "request", "response", "a client method", "TB081", blocks
                )
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
            where = f"{module.name()}.{cls.name}.{item.name}"
            annotations = [
                arg.annotation for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
            ]
            annotations.append(item.returns)
            for annotation in annotations:
                touched = self._domain_block_in(module, annotation, blocks)
                if touched is not None:
                    found.append(
                        Violation(
                            module.path(),
                            item.lineno,
                            "TB081",
                            f"{where} carries {KIND_NAME[touched]} in its signature; "
                            f"{subject} speaks records, never domain objects",
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
        where = f"{module.name()}.{cls.name}.__init__"
        for arg in self._params(init):
            if not self._allowed_annotation(module, arg.annotation, blocks, frozenset({"valueobject"})):
                found.append(
                    Violation(
                        module.path(),
                        init.lineno,
                        "TB080",
                        f"{where} parameter {arg.arg!r} is not allowed; "
                        "a value object constructs from primitives and value objects",
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
            where = f"{module.name()}.{cls.name}.{item.name}"
            if item.name != "__init__":
                found.append(
                    Violation(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{where} defines a method on a spec; a spec only carries construction data",
                    )
                )
                continue
            for arg in self._params(item):
                if not self._allowed_annotation(module, arg.annotation, blocks, frozenset({"valueobject", "spec"})):
                    found.append(
                        Violation(
                            module.path(),
                            item.lineno,
                            "TB080",
                            f"{where} parameter {arg.arg!r} is not allowed; "
                            "a spec field is a primitive, a value object, or a child spec",
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
            where = f"{module.name()}.{cls.name}.{item.name}"
            if item.name != "__init__":
                found.append(
                    Violation(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{where} defines a method on a DTO; a DTO carries data and nothing else",
                    )
                )
                continue
            for arg in self._params(item):
                if not self._allowed_annotation(module, arg.annotation, blocks, frozenset({"request", "response"})):
                    found.append(
                        Violation(
                            module.path(),
                            item.lineno,
                            "TB080",
                            f"{where} parameter {arg.arg!r} is not allowed; "
                            "a DTO field is a primitive or another DTO",
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
                    module.path(),
                    cls.lineno,
                    "TB080",
                    f"{module.name()}.{cls.name} defines no __init__; "
                    f"{subject} constructs from exactly one ts.Spec",
                ),
            )
        where = f"{module.name()}.{cls.name}.__init__"
        return self._signature_violations(
            module, where, init.lineno, init, "spec", None, "a domain constructor", "TB080", blocks
        )

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
                        base_key = module._resolve(base)
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
        line: int,
        fn: ast.FunctionDef,
        param_block: str,
        return_block: str | None,
        subject: str,
        code: str,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        expected = TS_NAME_BY_BLOCK[param_block]
        found: list[Violation] = []
        params = self._params(fn)
        if fn.args.vararg is not None or fn.args.kwarg is not None:
            found.append(
                Violation(
                    module.path(),
                    line,
                    code,
                    f"{where} uses *args/**kwargs; {subject} takes exactly one {expected}",
                )
            )
        if len(params) != 1:
            found.append(
                Violation(
                    module.path(),
                    line,
                    code,
                    f"{where} takes {len(params)} parameters; {subject} takes exactly one {expected}",
                )
            )
        for arg in params:
            if self._annotation_block(module, arg.annotation, blocks) != param_block:
                found.append(
                    Violation(
                        module.path(),
                        line,
                        code,
                        f"{where} parameter {arg.arg!r} is not a {expected}; "
                        f"{subject} takes exactly one {expected}",
                    )
                )
        if return_block is not None and self._annotation_block(module, fn.returns, blocks) != return_block:
            found.append(
                Violation(
                    module.path(),
                    line,
                    code,
                    f"{where} does not return a {TS_NAME_BY_BLOCK[return_block]}; "
                    f"{subject} returns a {TS_NAME_BY_BLOCK[return_block]}",
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
                found.append(
                    Violation(
                        module.path(),
                        node.lineno,
                        "TB082",
                        f"{where} delegates to self.{callee.attr}; a service inlines its logic",
                    )
                )
            elif isinstance(callee, ast.Name) and callee.id in functions:
                found.append(
                    Violation(
                        module.path(),
                        node.lineno,
                        "TB082",
                        f"{where} delegates to {callee.id}; a service inlines its logic",
                    )
                )
        return tuple(found)

    def _body_violations(self, module: Module, where: str, fn: ast.FunctionDef) -> tuple[Violation, ...]:
        found: list[Violation] = []
        first = fn.body[0].lineno
        last = fn.body[-1].end_lineno or fn.body[-1].lineno
        span = last - first + 1
        if span > 10:
            found.append(
                Violation(
                    module.path(),
                    fn.lineno,
                    "TB082",
                    f"{where} body spans {span} source lines; "
                    "a service method body is at most 10 source lines",
                )
            )
        for node in ast.walk(fn):
            if isinstance(node, ast.If):
                if not isinstance(node.test, ast.Call):
                    found.append(
                        Violation(
                            module.path(),
                            node.lineno,
                            "TB082",
                            f"{where} if condition is not a single call; "
                            "a service method satisfies a condition with one domain call",
                        )
                    )
                if self._contains_conditional(self._governed_stmts(node)):
                    found.append(
                        Violation(
                            module.path(),
                            node.lineno,
                            "TB082",
                            f"{where} nests a conditional; a service method branches one level deep",
                        )
                    )
            elif isinstance(node, ast.Match):
                if not isinstance(node.subject, ast.Call):
                    found.append(
                        Violation(
                            module.path(),
                            node.lineno,
                            "TB082",
                            f"{where} match subject is not a single call; "
                            "a service method satisfies a condition with one domain call",
                        )
                    )
                if self._contains_conditional([stmt for case in node.cases for stmt in case.body]):
                    found.append(
                        Violation(
                            module.path(),
                            node.lineno,
                            "TB082",
                            f"{where} nests a conditional; a service method branches one level deep",
                        )
                    )
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
                    module.path(),
                    lineno,
                    "TB050",
                    f"{module.name()} imports {target} inside a function; "
                    "a tesser import is module-level",
                )
            )
        for target, lineno in module.broken_relative_imports():
            found.append(
                Violation(
                    module.path(),
                    lineno,
                    "TB043",
                    f"{module.name()} imports {target} beyond the package root; "
                    "a relative import resolves inside the tree",
                )
            )
        return tuple(found)

    @staticmethod
    def _form_violations(module: Module, edge: ImportEdge) -> tuple[Violation, ...]:
        target = str(edge._target)
        lineno = int(edge._lineno)
        if str(edge._form) == "member":
            return (
                Violation(
                    module.path(),
                    lineno,
                    "TB053",
                    f"{module.name()} imports names from {target}; "
                    "a context module is imported as an aliased module, never its members",
                ),
            )
        if str(edge._form) == "bare":
            return (
                Violation(
                    module.path(),
                    lineno,
                    "TB053",
                    f"{module.name()} imports {target} without an alias; "
                    "a context module is imported as an aliased module, never its members",
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
            key = module._resolve(decorator)
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
            key = module._resolve(base)
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
                key = module._resolve(sub)
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
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left_none = isinstance(node.left, ast.Constant) and node.left.value is None
            right_none = isinstance(node.right, ast.Constant) and node.right.value is None
            if left_none == right_none:
                return False
            wrapped = node.right if left_none else node.left
            return self._allowed_annotation(module, wrapped, blocks, allowed_blocks)
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "tuple":
                elements = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
                return all(
                    self._allowed_annotation(module, element, blocks, allowed_blocks) for element in elements
                )
            return False
        key = module._resolve(node)
        return key is not None and blocks.get(key) in allowed_blocks

    def _annotation_block(
        self,
        module: Module,
        node: ast.expr | None,
        blocks: dict[tuple[str, str], str],
    ) -> str | None:
        if node is None:
            return None
        key = module._resolve(node)
        if key is None:
            return None
        return blocks.get(key)
