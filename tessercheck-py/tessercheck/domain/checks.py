import ast
import bisect
import builtins
import io
import re
import tokenize
import typing

import tesser.domain as ts
import tesser.serialization as serialization

TESSER_BASE_BLOCKS: typing.Final[dict[tuple[str, str], str]] = {
    ("tesser.application", "ApplicationService"): "service",
    ("tesser.application", "Mapper"): "mapper",
    ("tesser.application", "Port"): "port",
    ("tesser.application", "Store"): "store",
    ("tesser.application", "Request"): "port_request",
    ("tesser.application", "Response"): "port_response",
    ("tesser.application", "Client"): "actions_client",
    ("tesser.application", "Orchestrator"): "orchestrator",
    ("tesser.application", "Actions"): "actions",
    ("tesser.application", "JobContext"): "job_context",
    ("tesser.context", "Request"): "request",
    ("tesser.context", "Response"): "response",
    ("tesser.context", "Client"): "client",
    ("tesser.domain", "AggregateRoot"): "aggregate",
    ("tesser.domain", "Entity"): "entity",
    ("tesser.domain", "ValueObject"): "valueobject",
    ("tesser.domain", "Outcome"): "outcome",
    ("tesser.domain", "Spec"): "spec",
    ("tesser.adapters", "Repository"): "repository",
    ("tesser.adapters", "Gateway"): "gateway",
    ("tesser.adapters", "Handler"): "handler",
    ("tesser.adapters", "Job"): "job",
    ("tesser.adapters", "JobContext"): "job_context",
    ("tesser.testing", "JobContext"): "job_context",
    ("tesser.component", "Component"): "component",
    ("tesser.component", "Config"): "component_config",
    ("tesser.component", "Spec"): "component_spec",
    ("tesser.app", "App"): "app",
    ("tesser.app", "Loader"): "loader",
    ("tesser.app", "Config"): "app_config",
    ("tesser.app", "Spec"): "app_spec",
    ("tesser.app", "ConfigRepository"): "config_repository",
    ("tesser.srv", "Host"): "host",
    ("tesser.srv", "Port"): "protocol_port",
    ("tesser.srv", "Record"): "protocol_record",
    ("tesser.srv", "Rejection"): "protocol_rejection",
    ("tesser.srv", "Request"): "protocol_request",
    ("tesser.srv", "Response"): "protocol_response",
}

TESSER_ENTRY: typing.Final[tuple[str, str]] = ("tesser.srv", "main")

TESSER_DECORATORS: typing.Final[dict[tuple[str, str], str]] = {
    ("tesser.app", "load"): "load",
    ("tesser.testing", "helper"): "helper",
    ("tesser.testing", "fake"): "fake",
}

TS_NAME_BY_BLOCK: typing.Final[dict[str, str]] = {
    "request": "ts.Request",
    "response": "ts.Response",
    "port_request": "ts.Request",
    "port_response": "ts.Response",
    "spec": "ts.Spec",
    "app_spec": "ts.Spec",
    "component_spec": "ts.Spec",
}

ROLES: typing.Final[tuple[str, ...]] = ("domain", "application", "client", "adapters", "component")

STORE_METHOD: typing.Final[str] = "transaction"

STORE_RETURN: typing.Final[str] = "AsyncContextManager"

PORTS_PACKAGE: typing.Final[str] = "ports"

PORTS_PARENT_ROLE: typing.Final[str] = "application"

PORTS_HOME: typing.Final[str] = "application/ports"

PORTS_IMPORT_PATH: typing.Final[str] = "application.ports"

PORTS_KINDS: typing.Final[frozenset[str]] = frozenset({"port", "store", "port_request", "port_response"})

APPLICATION_CLIENT_PACKAGE: typing.Final[str] = "client"

APPLICATION_CLIENT_HOME: typing.Final[str] = "application/client"

APPLICATION_CLIENT_IMPORT: typing.Final[str] = "application.client"

ORCHESTRATORS_PACKAGE: typing.Final[str] = "orchestrators"

ORCHESTRATORS_HOME: typing.Final[str] = "application/orchestrators"

ORCHESTRATORS_IMPORT: typing.Final[str] = "application.orchestrators"

PACKAGE_HOMES: typing.Final[frozenset[str]] = frozenset(
    {PORTS_HOME, APPLICATION_CLIENT_HOME, ORCHESTRATORS_HOME}
)

JOB_ONLY_IMPORTS: typing.Final[tuple[str, ...]] = (
    APPLICATION_CLIENT_IMPORT,
    ORCHESTRATORS_IMPORT,
)

ADAPTER_BLOCKS: typing.Final[frozenset[str]] = frozenset(
    {"handler", "gateway", "repository", "job", "job_context"}
)

ADAPTER_KIND_PACKAGES: typing.Final[dict[str, frozenset[str]]] = {
    "handlers": frozenset({"handler"}),
    "gateways": frozenset({"gateway"}),
    "repositories": frozenset({"repository"}),
    "jobs": frozenset({"job", "job_context"}),
}

ADAPTER_KIND_REACH: typing.Final[dict[str, tuple[str, ...]]] = {
    "handlers": ("client",),
    "gateways": (PORTS_IMPORT_PATH,),
    "repositories": (PORTS_IMPORT_PATH,),
    "jobs": (APPLICATION_CLIENT_IMPORT, ORCHESTRATORS_IMPORT, PORTS_IMPORT_PATH),
}

HOST_KINDS: typing.Final[frozenset[str]] = frozenset({"handler", "job"})

APP_PACKAGES: typing.Final[tuple[str, ...]] = ("srv", "app")

APP_KINDS: typing.Final[frozenset[str]] = frozenset(
    {"app", "loader", "app_config", "app_spec", "config_repository"}
)

COMPONENT_KINDS: typing.Final[frozenset[str]] = frozenset(
    {"component", "component_config", "component_spec"}
)

KIND_ROLE: typing.Final[dict[str, str]] = {
    "aggregate": "domain",
    "entity": "domain",
    "valueobject": "domain",
    "outcome": "domain",
    "spec": "domain",
    "service": "application",
    "mapper": "application",
    "actions": "application",
    "orchestrator": ORCHESTRATORS_HOME,
    "actions_client": APPLICATION_CLIENT_HOME,
    "port": PORTS_HOME,
    "store": PORTS_HOME,
    "port_request": PORTS_HOME,
    "port_response": PORTS_HOME,
    "request": "client",
    "response": "client",
    "client": "client",
    "repository": "adapters",
    "gateway": "adapters",
    "handler": "adapters",
    "job": "adapters",
    "job_context": "adapters",
    "component": "component",
    "component_config": "component",
    "component_spec": "component",
}

KIND_HOME: typing.Final[dict[str, str]] = {
    block: (f"the {role} package" if role in PACKAGE_HOMES else f"{role}.py")
    for block, role in KIND_ROLE.items()
}

KIND_NAME: typing.Final[dict[str, str]] = {
    "aggregate": "an aggregate",
    "entity": "an entity",
    "valueobject": "a value object",
    "outcome": "an outcome",
    "spec": "a spec",
    "service": "a service",
    "mapper": "a mapper",
    "actions": "a class of actions",
    "orchestrator": "an orchestrator",
    "actions_client": "an application client",
    "port": "a port",
    "store": "a store",
    "port_request": "a port request DTO",
    "port_response": "a port response DTO",
    "request": "a request DTO",
    "response": "a response DTO",
    "client": "a client",
    "repository": "a repository adapter",
    "gateway": "a gateway adapter",
    "handler": "an inbound handler",
    "job": "a job",
    "job_context": "a job context",
    "component": "a component",
    "component_config": "a component config",
    "component_spec": "a component config spec",
    "app": "an app",
    "loader": "an app loader",
    "app_config": "an app config",
    "app_spec": "an app config spec",
    "config_repository": "a config repository",
    "host": "a host",
    "protocol_port": "a protocol port",
    "protocol_record": "a protocol record",
    "protocol_rejection": "a protocol rejection",
    "protocol_request": "a protocol request record",
    "protocol_response": "a protocol response record",
}

SRV_KINDS: typing.Final[frozenset[str]] = frozenset(
    block for (package, _), block in TESSER_BASE_BLOCKS.items() if package == "tesser.srv"
)

PROTOCOL_KINDS: typing.Final[frozenset[str]] = SRV_KINDS - frozenset({"host"})

PROTOCOL_PACKAGE: typing.Final[str] = "protocol"

TREE_DECLARATION: typing.Final[str] = ".tesser-root"

DECLARED_APP: typing.Final[str] = "app"

DECLARED_MISSING: typing.Final[str] = "missing"

DECLARED_UNREADABLE: typing.Final[str] = "unreadable"

DECLARED_UNRECOGNIZED: typing.Final[str] = "unrecognized"

DO_NOT_USE_PREFIX: typing.Final[str] = "do_not_use_"

KERNEL_PACKAGE: typing.Final[str] = "kernel"

TESSER: typing.Final[str] = "tesser"

TESSER_NAMESPACES: typing.Final[frozenset[str]] = frozenset(
    {
        "app",
        "component",
        "domain",
        "application",
        "adapters",
        "context",
        "srv",
        "testing",
        "errors",
        "serialization",
    }
)

TESSER_STDLIB: typing.Final[frozenset[str]] = frozenset(
    {
        "__future__",
        "typing",
        "collections",
        "enum",
        "datetime",
        "decimal",
        "sys",
    }
)

STUB_SUFFIX: typing.Final[str] = ".pyi"

IMPORTLIB: typing.Final[str] = "importlib"

BUILTIN_IMPORT: typing.Final[str] = "__import__"

BUILTINS: typing.Final[str] = "builtins"

SYS_MODULE: typing.Final[str] = "sys"

DEBT_MARKER: typing.Final[str] = "tesser:debt"

DEBT_FILE_MARKER: typing.Final[str] = "tesser:debt-file"

CODE_SHAPE: typing.Final[re.Pattern[str]] = re.compile(r"TB[0-9]{3}\Z")

DIRECTIVE: typing.Final[re.Pattern[str]] = re.compile(
    r"^#\s*(!|type:|noqa|tesser:debt(-file)?(?![\w-])|pragma|fmt:|isort:|ruff:)"
)

CODING_DECL: typing.Final[re.Pattern[str]] = re.compile(r"^#.*?coding[:=]\s*[-\w.]+")

MUTABLE_COLLECTIONS: typing.Final[frozenset[str]] = frozenset(
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

MOCK_MODULES: typing.Final[frozenset[str]] = frozenset({"unittest.mock", "mock"})

PATCHER_FIXTURES: typing.Final[frozenset[str]] = frozenset({"monkeypatch", "mocker"})

BUILTIN_NAMES: typing.Final[frozenset[str]] = frozenset(
    name for name in dir(builtins) if not name.startswith("_")
)

ROLE_TESSER_PACKAGE: typing.Final[dict[str, str]] = {
    "domain": "tesser.domain",
    "application": "tesser.application",
    "client": "tesser.context",
    "adapters": "tesser.adapters",
    "component": "tesser.component",
}

DECLARATION_BLOCKS: typing.Final[frozenset[str]] = frozenset(
    {
        "request",
        "response",
        "client",
        "actions_client",
        "port",
        "port_request",
        "port_response",
        "protocol_port",
        "protocol_record",
        "protocol_rejection",
        "protocol_request",
        "protocol_response",
    }
)

DATA_BLOCKS: typing.Final[frozenset[str]] = frozenset(
    {
        "spec",
        "app_spec",
        "component_spec",
        "request",
        "response",
        "port_request",
        "port_response",
        "protocol_record",
        "protocol_rejection",
        "protocol_request",
        "protocol_response",
    }
)

PAIRED_PLACES: typing.Final[frozenset[str]] = frozenset(
    {"role", "kernel", "shell-srv", "shell-app", "protocol", ORCHESTRATORS_PACKAGE}
)

NORM_IMPORTS: typing.Final[dict[str, frozenset[str]]] = {
    "domain": frozenset({"tesser.errors", "tesser.serialization"}),
    "application": frozenset({"tesser.errors"}),
    "adapters": frozenset({"tesser.errors"}),
    "component": frozenset({"tesser.errors"}),
    "app": frozenset({"tesser.errors"}),
    "srv": frozenset({"tesser.errors"}),
    "test": frozenset(
        {"tesser.app", "tesser.errors", "tesser.serialization"}
    ),
}

SAME_CONTEXT_IMPORTS: typing.Final[dict[str, tuple[str, ...]]] = {
    "domain": (),
    "client": (),
    "application": ("domain", "client"),
    "adapters": (PORTS_IMPORT_PATH,),
    "component": ("application", "adapters", "client"),
}

TESTS_ROLE: typing.Final[str] = "tests"

EVAL_PREFIX: typing.Final[str] = "eval_"

EVAL_HOME: typing.Final[str] = "gateways"

TEST_TIER_HOME: typing.Final[dict[str, tuple[str, str | None]]] = {
    "domain": ("domain", None),
    "application": ("application", None),
    "client": ("client", None),
    "component": ("component", None),
    "handlers": ("adapters", "handlers"),
    "gateways": ("adapters", "gateways"),
    "repositories": ("adapters", "repositories"),
    "jobs": ("adapters", "jobs"),
    ORCHESTRATORS_PACKAGE: ("application", ORCHESTRATORS_PACKAGE),
}

TEST_TIER_REACH: typing.Final[dict[str, tuple[str, ...]]] = {
    "domain": SAME_CONTEXT_IMPORTS["domain"],
    "application": SAME_CONTEXT_IMPORTS["application"],
    "client": SAME_CONTEXT_IMPORTS["client"],
    "component": SAME_CONTEXT_IMPORTS["component"],
    "handlers": ("client",),
    "gateways": SAME_CONTEXT_IMPORTS["adapters"],
    "repositories": SAME_CONTEXT_IMPORTS["adapters"],
    "jobs": ADAPTER_KIND_REACH["jobs"],
    ORCHESTRATORS_PACKAGE: SAME_CONTEXT_IMPORTS["application"]
    + (ORCHESTRATORS_IMPORT, PORTS_IMPORT_PATH),
    TESTS_ROLE: ROLES + (TESTS_ROLE,),
}

TEST_TIER_FOREIGN: typing.Final[dict[str, tuple[str, ...]]] = {
    "gateways": ("client",),
    "component": ("client",),
    TESTS_ROLE: ("application", "client"),
}

ADAPTER_TEST_TIERS: typing.Final[frozenset[str]] = frozenset(
    {"handlers", "gateways", "repositories", "jobs"}
)

SRV_TIER: typing.Final[str] = "srv"

APP_TIER: typing.Final[str] = "an app"

PROTOCOL_TIER: typing.Final[str] = "protocol"

STRAY_TIER: typing.Final[str] = "stray"

ROOT_TESTS_TIER: typing.Final[str] = "the root tests package"

SHELL_PACKAGES: typing.Final[frozenset[str]] = frozenset(APP_PACKAGES) | {PROTOCOL_PACKAGE, TESTS_ROLE}

KERNEL_TIER: typing.Final[str] = "kernel"

TEST_TIER_SHELL: typing.Final[dict[str, frozenset[str]]] = {
    ROOT_TESTS_TIER: SHELL_PACKAGES,
    SRV_TIER: frozenset({"srv", "app", "protocol"}),
    APP_TIER: frozenset({"app"}),
    PROTOCOL_TIER: frozenset({"protocol"}),
    KERNEL_TIER: frozenset(),
    "domain": frozenset(),
    "application": frozenset(),
    "client": frozenset(),
    "component": frozenset(),
    "handlers": frozenset({"protocol"}),
    "gateways": frozenset(),
    "repositories": frozenset(),
    "jobs": frozenset(),
    ORCHESTRATORS_PACKAGE: frozenset(),
    TESTS_ROLE: frozenset({"protocol"}),
}

PRIMITIVES: typing.Final[frozenset[str]] = frozenset({"str", "int", "float", "bool", "bytes"})

MAPPER_PREFIX: typing.Final[str] = "MapTo"

PORT_DTO_PRIMITIVES: typing.Final[frozenset[str]] = PRIMITIVES - frozenset({"bool"})

JOB_CONTEXT_BLOCK: typing.Final[str] = "job_context"

ENUM_BASES: typing.Final[frozenset[str]] = frozenset({"Enum"})

ENUM_MODULE: typing.Final[str] = "enum"

FUTURE_MODULE: typing.Final[str] = "__future__"

CORE_STDLIB: typing.Final[dict[str, frozenset[str]]] = {
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
            "collections.abc",
            "urllib.parse",
            "copy",
        }
    ),
    "client": frozenset({"__future__", "typing"}),
    "application": frozenset({"__future__", "typing"}),
}

PORTS_STDLIB: typing.Final[frozenset[str]] = frozenset({"__future__", "typing", "enum"})

DOMAIN_BLOCKS: typing.Final[frozenset[str]] = frozenset({"aggregate", "entity", "valueobject"})

OUTCOME_BLOCK: typing.Final[str] = "outcome"

OUTCOME_BASE: typing.Final[tuple[str, str]] = ("tesser.domain", "Outcome")

DOMAIN_OBJECT_BLOCKS: typing.Final[frozenset[str]] = DOMAIN_BLOCKS | frozenset({OUTCOME_BLOCK})

DOMAIN_METHOD_PARAMETER_BLOCKS: typing.Final[frozenset[str]] = DOMAIN_BLOCKS | frozenset(
    {"spec"}
)

ASSERT_NEVER: typing.Final[str] = "assert_never"

OUTCOME_SUNDERS: typing.Final[frozenset[str]] = frozenset({"_value_", "_name_"})

TYPING_MODULE: typing.Final[str] = "typing"

SPEC_BLOCKS: typing.Final[frozenset[str]] = frozenset({"spec", "component_spec", "app_spec"})

PUBLIC_CALL: typing.Final[str] = "__call__"

CONTAINER_NAMES: typing.Final[frozenset[str]] = MUTABLE_COLLECTIONS | frozenset(
    {
        "tuple",
        "Tuple",
        "frozenset",
        "FrozenSet",
        "Sequence",
        "Iterable",
        "Collection",
        "Mapping",
    }
)

SPEC_READER_BLOCKS: typing.Final[frozenset[str]] = DOMAIN_BLOCKS | frozenset(
    {"component_config", "app_config"}
)

TEST_TIER: typing.Final[frozenset[str]] = frozenset({"test", "conftest", "conftest-root", "eval"})

WRAPPABLE_SCALARS: typing.Final[frozenset[str]] = frozenset(
    {"str", "int", "float", "bytes", "Decimal", "date", "datetime", "time"}
)

NON_WRAPPABLE_SCALARS: typing.Final[frozenset[str]] = frozenset({"bool", "complex"})

DOMAIN_METHOD_PRIMITIVES: typing.Final[frozenset[str]] = (
    PRIMITIVES | WRAPPABLE_SCALARS | NON_WRAPPABLE_SCALARS
)

CANONICAL_EXIT: typing.Final[dict[str, str]] = {
    "str": "__str__",
    "int": "__int__",
    "float": "__float__",
    "bytes": "__bytes__",
    "Decimal": "__str__",
    "date": "__str__",
    "datetime": "__str__",
    "time": "__str__",
}

CONVERSION_DUNDERS: typing.Final[frozenset[str]] = frozenset(
    {"__str__", "__int__", "__float__", "__bytes__"}
)

CANONICAL_HELPER: typing.Final[dict[str, str]] = {
    "str": "canonical_str",
    "int": "canonical_int",
    "float": "canonical_float",
    "bytes": "canonical_bytes",
    "Decimal": "canonical_decimal",
    "datetime": "canonical_datetime",
}

LANGUAGE_FIXED: typing.Final[frozenset[str]] = frozenset(
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

COMPARISON_DUNDERS: typing.Final[frozenset[str]] = frozenset(
    {"__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__"}
)

COMPARISON_CALLS: typing.Final[frozenset[str]] = COMPARISON_DUNDERS | frozenset(
    {"__contains__", "__bool__"}
)

OPERATOR_MODULE: typing.Final[str] = "operator"

OPERATOR_COMPARISONS: typing.Final[frozenset[str]] = frozenset(
    {"eq", "ne", "lt", "le", "gt", "ge", "contains", "not_", "truth", "is_", "is_not"}
)

TRUTH_BUILTINS: typing.Final[frozenset[str]] = frozenset({"bool", "any", "all"})

RETURN_WRAPPERS: typing.Final[frozenset[str]] = frozenset(
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

SELF_NAMES: typing.Final[frozenset[str]] = frozenset({"Self", "Never", "NoReturn", "None"})


class TreeRoot(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("tree root must be non-empty")
        if value.endswith("/") and value != "/":
            raise ValueError("tree root carries no trailing separator")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Path(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("path must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Line(ts.ValueObject):

    _value: int

    def __init__(self, value: int) -> None:
        if value < 1:
            raise ValueError("line must be positive")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return serialization.canonical_int(self._value)


class Code(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not CODE_SHAPE.match(value):
            raise ValueError("code must be a TB0xx family code")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Text(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("text must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Target(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("target must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class EdgeForm(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("member", "aliased", "bare"):
            raise ValueError("edge form must be member, aliased, or bare")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class ImportForm(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("from", "ts", "alias", "bare"):
            raise ValueError("import form must be from, ts, alias, or bare")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class DebtScope(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("line", "file"):
            raise ValueError("debt scope must be line or file")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class DebtForm(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("parsed", "malformed"):
            raise ValueError("debt form must be parsed or malformed")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class SymbolSpec(ts.Spec):

    def __init__(self, module: str, name: str) -> None:
        self.module = module
        self.name = name


class Symbol(ts.ValueObject):

    _module: Text
    _name: Text

    def __init__(self, spec: SymbolSpec) -> None:
        object.__setattr__(self, "_module", Text(spec.module))
        object.__setattr__(self, "_name", Text(spec.name))

    def module(self) -> Text:
        return self._module

    def name(self) -> Text:
        return self._name


class SpecShape(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if value not in ("one", "many"):
            raise ValueError("spec shape must be one or many")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class SpecRefSpec(ts.Spec):

    def __init__(self, symbol: SymbolSpec, shape: str) -> None:
        self.symbol = symbol
        self.shape = shape


class SpecRef(ts.ValueObject):

    _symbol: Symbol
    _shape: SpecShape

    def __init__(self, spec: SpecRefSpec) -> None:
        object.__setattr__(self, "_symbol", Symbol(spec.symbol))
        object.__setattr__(self, "_shape", SpecShape(spec.shape))

    def symbol(self) -> Symbol:
        return self._symbol

    def shape(self) -> SpecShape:
        return self._shape

    def one(self) -> "SpecRef":
        return SpecRef(SpecRefSpec(SymbolSpec(str(self._symbol.module()), str(self._symbol.name())), "one"))

    def many(self) -> "SpecRef":
        return SpecRef(SpecRefSpec(SymbolSpec(str(self._symbol.module()), str(self._symbol.name())), "many"))


SPEC_ONE: typing.Final[SpecShape] = SpecShape("one")

SPEC_MANY: typing.Final[SpecShape] = SpecShape("many")


class ViolationSpec(ts.Spec):

    def __init__(self, path: str, line: int, code: str, message: str) -> None:
        self.path = path
        self.line = line
        self.code = code
        self.message = message


class Violation(ts.ValueObject):

    _path: Path
    _line: Line
    _code: Code
    _text: Text

    def __init__(self, spec: ViolationSpec) -> None:
        object.__setattr__(self, "_path", Path(spec.path))
        object.__setattr__(self, "_line", Line(spec.line))
        object.__setattr__(self, "_code", Code(spec.code))
        object.__setattr__(self, "_text", Text(spec.message))

    def path(self) -> Path:
        return self._path

    def line(self) -> Line:
        return self._line

    def code(self) -> Code:
        return self._code

    def text(self) -> Text:
        return self._text


class DebtSpec(ts.Spec):

    def __init__(
        self, line: int, codes: tuple[str, ...], file_level: bool, form: str = "parsed"
    ) -> None:
        self.line = line
        self.codes = codes
        self.file_level = file_level
        self.form = form


class Debt(ts.ValueObject):

    _line: Line
    _codes: tuple[Code, ...]
    _scope: DebtScope
    _form: DebtForm

    def __init__(self, spec: DebtSpec) -> None:
        object.__setattr__(self, "_line", Line(spec.line))
        object.__setattr__(self, "_codes", tuple(Code(code) for code in spec.codes))
        object.__setattr__(
            self, "_scope", DebtScope("file" if spec.file_level else "line")
        )
        object.__setattr__(self, "_form", DebtForm(spec.form))


class ImportEdgeSpec(ts.Spec):

    def __init__(
        self, target: str, lineno: int, member_form: bool, aliased: bool, path: str = "", module: str = ""
    ) -> None:
        self.target = target
        self.lineno = lineno
        self.member_form = member_form
        self.aliased = aliased
        self.path = path
        self.module = module


class ImportEdge(ts.ValueObject):

    _target: Target
    _lineno: Line
    _form: EdgeForm
    _path: Path | None
    _module: Text | None

    def __init__(self, spec: ImportEdgeSpec) -> None:
        object.__setattr__(self, "_target", Target(spec.target))
        object.__setattr__(self, "_lineno", Line(spec.lineno))
        object.__setattr__(
            self,
            "_form",
            EdgeForm("member" if spec.member_form else "aliased" if spec.aliased else "bare"),
        )
        object.__setattr__(self, "_path", Path(spec.path) if spec.path else None)
        object.__setattr__(self, "_module", Text(spec.module) if spec.module else None)

    def member_form_violations(self) -> tuple[Violation, ...]:
        name = str(self._module)
        target = str(self._target)
        if str(self._form) != "member" or target == FUTURE_MODULE:
            return ()
        return (
            Violation(ViolationSpec(
                str(self._path),
                int(self._lineno),
                "TB053",
                f"{name} imports names from {target}; "
                "every import is a module import — import x or import x as name, "
                "never from x import name",
            )),
        )



class TesserImportSpec(ts.Spec):

    def __init__(
        self, target: str, lineno: int, as_ts: bool, from_form: bool, bare: bool = False
    ) -> None:
        self.target = target
        self.lineno = lineno
        self.as_ts = as_ts
        self.from_form = from_form
        self.bare = bare


class TesserImport(ts.ValueObject):

    _target: Target
    _lineno: Line
    _form: ImportForm

    def __init__(self, spec: TesserImportSpec) -> None:
        object.__setattr__(self, "_target", Target(spec.target))
        object.__setattr__(self, "_lineno", Line(spec.lineno))
        object.__setattr__(
            self,
            "_form",
            ImportForm(
                "from"
                if spec.from_form
                else "ts"
                if spec.as_ts
                else "bare"
                if spec.bare
                else "alias"
            ),
        )


class CommentSpec(ts.Spec):

    def __init__(self, line: int, text: str) -> None:
        self.line = line
        self.text = text


class Comment(ts.ValueObject):

    _line: Line
    _text: Text

    def __init__(self, spec: CommentSpec) -> None:
        object.__setattr__(self, "_line", Line(spec.line))
        object.__setattr__(self, "_text", Text(spec.text))


BODY_BLOCKS: typing.Final[frozenset[str]] = frozenset(
    {"service", "actions", "orchestrator", "repository", "gateway", "handler"}
)


class Names(ts.ValueObject):

    _items: tuple[str, ...]

    def __init__(self, items: tuple[str, ...]) -> None:
        object.__setattr__(self, "_items", tuple(sorted(frozenset(items))))

    def __and__(self, other: "Names") -> "Names":
        return Names(tuple(item for item in self._items if item in other._items))

    def __sub__(self, other: "Names") -> "Names":
        return Names(tuple(item for item in self._items if item not in other._items))

    def __or__(self, other: "Names") -> "Names":
        return Names(self._items + other._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __contains__(self, item: object) -> bool:
        return item in self._items

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._items)


SCALAR_NAMES: typing.Final[Names] = Names(tuple(WRAPPABLE_SCALARS | NON_WRAPPABLE_SCALARS))

WRAPPABLE_NAMES: typing.Final[Names] = Names(tuple(WRAPPABLE_SCALARS))

CONSTRUCTOR_DECORATORS: typing.Final[Names] = Names(("classmethod", "staticmethod"))

RETURN_SKIPPED: typing.Final[Names] = Names(tuple(RETURN_WRAPPERS | SELF_NAMES))


class SymbolsSpec(ts.Spec):

    def __init__(self, items: tuple[SymbolSpec, ...]) -> None:
        self.items = items


class Symbols(ts.ValueObject):

    _items: tuple[Symbol, ...]

    def __init__(self, spec: SymbolsSpec) -> None:
        object.__setattr__(self, "_items", tuple(Symbol(item) for item in spec.items))

    def __and__(self, other: "Symbols") -> "Symbols":
        return Symbols(SymbolsSpec(tuple(
            SymbolSpec(str(item.module()), str(item.name()))
            for item in self._items
            if item in other._items
        )))

    def __bool__(self) -> bool:
        return bool(self._items)

    def __contains__(self, item: object) -> bool:
        return item in self._items

    def __iter__(self) -> typing.Iterator[Symbol]:
        return iter(self._items)


class KindTableSpec(ts.Spec):

    def __init__(self, entries: tuple[tuple[str, str, str], ...]) -> None:
        self.entries = entries


class KindTable(ts.ValueObject):

    _symbols: tuple[Symbol, ...]
    _blocks: tuple[Text, ...]

    def __init__(self, spec: KindTableSpec) -> None:
        ordered = sorted(spec.entries)
        object.__setattr__(
            self, "_symbols", tuple(Symbol(SymbolSpec(module, name)) for module, name, _ in ordered)
        )
        object.__setattr__(self, "_blocks", tuple(Text(block) for _, _, block in ordered))

    def block_of(self, symbol: Symbol) -> Text | None:
        wanted = (str(symbol.module()), str(symbol.name()))
        index = bisect.bisect_left(
            self._symbols, wanted, key=lambda item: (str(item.module()), str(item.name()))
        )
        if index < len(self._symbols) and self._symbols[index] == symbol:
            return self._blocks[index]
        return None


class RegistrySpec(ts.Spec):

    def __init__(
        self,
        kinds: KindTableSpec,
        domain_enums: tuple[SymbolSpec, ...],
        outcome_methods: tuple[str, ...] = (),
        action_ports: tuple[SymbolSpec, ...] = (),
    ) -> None:
        self.kinds = kinds
        self.domain_enums = domain_enums
        self.outcome_methods = outcome_methods
        self.action_ports = action_ports


class Registry(ts.ValueObject):

    _kinds: KindTable
    _domain_enums: Symbols
    _outcome_methods: Names
    _action_ports: Symbols

    def __init__(self, spec: RegistrySpec) -> None:
        object.__setattr__(self, "_kinds", KindTable(spec.kinds))
        object.__setattr__(self, "_domain_enums", Symbols(SymbolsSpec(spec.domain_enums)))
        object.__setattr__(self, "_outcome_methods", Names(spec.outcome_methods))
        object.__setattr__(self, "_action_ports", Symbols(SymbolsSpec(spec.action_ports)))

    def kinds(self) -> KindTable:
        return self._kinds

    def domain_enums(self) -> Symbols:
        return self._domain_enums

    def outcome_methods(self) -> Names:
        return self._outcome_methods

    def action_ports(self) -> Symbols:
        return self._action_ports


class ImportSpec(ts.Spec):

    def __init__(self, local: str, target: str, original: str) -> None:
        self.local = local
        self.target = target
        self.original = original


class Import(ts.ValueObject):

    _local: Text
    _target: Text
    _original: Text

    def __init__(self, spec: ImportSpec) -> None:
        object.__setattr__(self, "_local", Text(spec.local))
        object.__setattr__(self, "_target", Text(spec.target))
        object.__setattr__(self, "_original", Text(spec.original))

    def local(self) -> Text:
        return self._local

    def target(self) -> Text:
        return self._target

    def original(self) -> Text:
        return self._original


class AliasSpec(ts.Spec):

    def __init__(self, alias: str, package: str) -> None:
        self.alias = alias
        self.package = package


class Alias(ts.ValueObject):

    _alias: Text
    _package: Text

    def __init__(self, spec: AliasSpec) -> None:
        object.__setattr__(self, "_alias", Text(spec.alias))
        object.__setattr__(self, "_package", Text(spec.package))

    def alias(self) -> Text:
        return self._alias

    def package(self) -> Text:
        return self._package


class ScopeSpec(ts.Spec):

    def __init__(
        self,
        module: str,
        imported: tuple[ImportSpec, ...],
        packages: tuple[AliasSpec, ...],
        classes: tuple[str, ...],
        functions: tuple[str, ...] = (),
        spoken: str | None = None,
    ) -> None:
        self.module = module
        self.imported = imported
        self.packages = packages
        self.classes = classes
        self.functions = functions
        self.spoken = spoken


class Scope(ts.ValueObject):

    _module: Text
    _imported: tuple[Import, ...]
    _packages: tuple[Alias, ...]
    _classes: Names
    _functions: Names
    _spoken: Text | None

    def __init__(self, spec: ScopeSpec) -> None:
        object.__setattr__(self, "_module", Text(spec.module))
        object.__setattr__(self, "_imported", tuple(Import(item) for item in spec.imported))
        object.__setattr__(self, "_packages", tuple(Alias(item) for item in spec.packages))
        object.__setattr__(self, "_classes", Names(spec.classes))
        object.__setattr__(self, "_functions", Names(spec.functions))
        object.__setattr__(self, "_spoken", Text(spec.spoken) if spec.spoken else None)

    def functions(self) -> Names:
        return self._functions

    def classes(self) -> Names:
        return self._classes

    def spoken(self) -> Text | None:
        return self._spoken

    def locals(self) -> Names:
        return Names(tuple(str(binding.local()) for binding in self._imported) + tuple(str(alias.alias()) for alias in self._packages))

    def package_of(self, alias: Text) -> Text | None:
        for item in self._packages:
            if item.alias() == alias:
                return item.package()
        return None

    def import_of(self, local: Text) -> Symbol | None:
        for binding in self._imported:
            if binding.local() == local:
                return Symbol(SymbolSpec(str(binding.target()), str(binding.original())))
        return None

    def resolve(self, ref: Text) -> Symbol | None:
        wanted = str(ref)
        if "." in wanted:
            prefix, attr = wanted.rsplit(".", 1)
            for alias in self._packages:
                if str(alias.alias()) == prefix:
                    return Symbol(SymbolSpec(str(alias.package()), attr))
            return None
        for binding in self._imported:
            if str(binding.local()) == wanted:
                return Symbol(SymbolSpec(str(binding.target()), str(binding.original())))
        if wanted in self._classes:
            return Symbol(SymbolSpec(str(self._module), wanted))
        return None

    def symbols(self, annotation: "Annotation") -> Symbols:
        found: list[tuple[str, str]] = []
        for ref in annotation.refs():
            if "." in ref:
                prefix, attr = ref.rsplit(".", 1)
                for alias in self._packages:
                    if str(alias.alias()) == prefix:
                        found.append((str(alias.package()), attr))
                continue
            for binding in self._imported:
                if str(binding.local()) == ref:
                    found.append((str(binding.target()), str(binding.original())))
            if ref in self._classes:
                found.append((str(self._module), ref))
        return Symbols(SymbolsSpec(tuple(SymbolSpec(module_name, name) for module_name, name in found)))


class Annotation(ts.ValueObject):

    _dump: Text
    _source: Text
    _head: Text | None
    _container: Text | None
    _scalars: Names
    _refs: Names
    _produced: Names
    _produced_refs: Names
    _leaves: Names | None
    _primary: Text | None
    _quoted: Names
    _slice_names: Names

    def __init__(self, node: ast.expr) -> None:  # tesser:debt TB080
        slice_names: list[str] = []
        sliced = node
        if isinstance(sliced, ast.Constant) and isinstance(sliced.value, str):
            try:
                sliced = ast.parse(sliced.value, mode="eval").body
            except SyntaxError:
                sliced = node
        if isinstance(sliced, ast.Subscript):
            elements = sliced.slice.elts if isinstance(sliced.slice, ast.Tuple) else [sliced.slice]
            for element in elements:
                if isinstance(element, ast.Name):
                    slice_names.append(element.id)
                elif isinstance(element, ast.Attribute) and isinstance(element.value, (ast.Name, ast.Attribute)):
                    slice_names.append(f"{ast.unparse(element.value)}.{element.attr}")
                elif not (isinstance(element, ast.Constant) and element.value is Ellipsis):
                    slice_names.append("?")
        primary: ast.expr = node
        quote_marks: list[str] = []
        if isinstance(primary, ast.Constant) and isinstance(primary.value, str):
            quote_marks.append("quoted")
            try:
                primary = ast.parse(primary.value, mode="eval").body
            except SyntaxError:
                primary = node
        while isinstance(primary, ast.Subscript):
            primary = primary.value
        primary_ref: str | None = None
        if isinstance(primary, ast.Name):
            primary_ref = primary.id
        elif isinstance(primary, ast.Attribute) and isinstance(primary.value, (ast.Name, ast.Attribute)):
            primary_ref = f"{ast.unparse(primary.value)}.{primary.attr}"
        cursor: ast.expr | None = node
        head: str | None = None
        while cursor is not None:
            if isinstance(cursor, ast.Name):
                head = cursor.id
                break
            if isinstance(cursor, ast.Attribute):
                head = cursor.attr
                break
            if isinstance(cursor, ast.Subscript):
                cursor = cursor.value
                continue
            if isinstance(cursor, ast.Constant) and isinstance(cursor.value, str):
                try:
                    parsed = ast.parse(cursor.value, mode="eval").body
                except SyntaxError:
                    break
                cursor = None if isinstance(parsed, ast.Constant) else parsed
                continue
            break
        container: str | None = None
        pending: list[ast.expr] = [node]
        while pending and container is None:
            probe = pending.pop()
            if isinstance(probe, ast.Constant) and isinstance(probe.value, str):
                try:
                    probe = ast.parse(probe.value, mode="eval").body
                except SyntaxError:
                    continue
            if isinstance(probe, ast.BinOp) and isinstance(probe.op, ast.BitOr):
                pending.extend([probe.left, probe.right])
                continue
            if isinstance(probe, ast.Subscript):
                wrapper: ast.expr = probe.value
                wrapper_head = (
                    wrapper.id
                    if isinstance(wrapper, ast.Name)
                    else wrapper.attr
                    if isinstance(wrapper, ast.Attribute)
                    else None
                )
                if wrapper_head in ("Optional", "Final", "Annotated"):
                    wrapped = probe.slice
                    if isinstance(wrapped, ast.Tuple) and wrapped.elts:
                        wrapped = wrapped.elts[0]
                    pending.append(wrapped)
                    continue
                probe = probe.value
            if isinstance(probe, ast.Attribute) and probe.attr in CONTAINER_NAMES:
                container = probe.attr
            elif isinstance(probe, ast.Name) and probe.id in CONTAINER_NAMES:
                container = probe.id
        names: set[str] = set()
        refs: set[str] = set()
        stack: list[ast.AST] = [node]
        while stack:
            top = stack.pop()
            for sub in ast.walk(top):
                if isinstance(sub, ast.Name):
                    names.add(sub.id)
                    refs.add(sub.id)
                elif isinstance(sub, ast.Attribute):
                    names.add(sub.attr)
                    if isinstance(sub.value, (ast.Name, ast.Attribute)):
                        refs.add(f"{ast.unparse(sub.value)}.{sub.attr}")
                elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    try:
                        quoted = ast.parse(sub.value, mode="eval").body
                    except SyntaxError:
                        continue
                    if not isinstance(quoted, ast.Constant):
                        stack.append(quoted)
        produced: set[str] = set()
        produced_refs: set[str] = set()
        walk_stack: list[ast.expr] = [node]
        while walk_stack:
            walked = walk_stack.pop()
            if isinstance(walked, ast.Subscript):
                inner: ast.expr = walked.value
                while isinstance(inner, ast.Subscript):
                    inner = inner.value
                inner_head = (
                    inner.id
                    if isinstance(inner, ast.Name)
                    else inner.attr
                    if isinstance(inner, ast.Attribute)
                    else None
                )
                if inner_head not in ("type", "Type", "Callable"):
                    walk_stack.append(walked.slice)
                continue
            if isinstance(walked, ast.Constant):
                if isinstance(walked.value, str):
                    try:
                        parsed_walk = ast.parse(walked.value, mode="eval")
                    except SyntaxError:
                        continue
                    if not isinstance(parsed_walk.body, ast.Constant):
                        walk_stack.append(parsed_walk.body)
                continue
            if isinstance(walked, ast.Attribute):
                produced.add(walked.attr)
                if isinstance(walked.value, (ast.Name, ast.Attribute)):
                    produced_refs.add(f"{ast.unparse(walked.value)}.{walked.attr}")
                continue
            if isinstance(walked, ast.Name):
                produced.add(walked.id)
                produced_refs.add(walked.id)
                continue
            walk_stack.extend(
                child for child in ast.iter_child_nodes(walked) if isinstance(child, ast.expr)
            )
        leaves: list[str] | None = []
        peel: list[ast.expr] = [node]
        while peel and leaves is not None:
            leaf = peel.pop()
            if isinstance(leaf, ast.Constant):
                if isinstance(leaf.value, str):
                    try:
                        peel.append(ast.parse(leaf.value, mode="eval").body)
                    except SyntaxError:
                        leaves = None
                    continue
                if leaf.value is Ellipsis or leaf.value is None:
                    continue
                leaves = None
                continue
            if isinstance(leaf, ast.Name):
                leaves.append(leaf.id)
                continue
            if isinstance(leaf, ast.Attribute) and isinstance(leaf.value, (ast.Name, ast.Attribute)):
                leaves.append(f"{ast.unparse(leaf.value)}.{leaf.attr}")
                continue
            if isinstance(leaf, ast.BinOp) and isinstance(leaf.op, ast.BitOr):
                left_none = isinstance(leaf.left, ast.Constant) and leaf.left.value is None
                right_none = isinstance(leaf.right, ast.Constant) and leaf.right.value is None
                if left_none == right_none:
                    leaves = None
                    continue
                peel.append(leaf.right if left_none else leaf.left)
                continue
            if isinstance(leaf, ast.Subscript) and isinstance(leaf.value, ast.Name) and leaf.value.id == "tuple":
                peel.extend(leaf.slice.elts if isinstance(leaf.slice, ast.Tuple) else [leaf.slice])
                continue
            leaves = None
        object.__setattr__(self, "_dump", Text(ast.dump(node)))
        object.__setattr__(self, "_source", Text(ast.unparse(node)))
        object.__setattr__(self, "_head", Text(head) if head else None)
        object.__setattr__(self, "_container", Text(container) if container else None)
        object.__setattr__(
            self, "_scalars", Names(tuple(names - RETURN_WRAPPERS - SELF_NAMES))
        )
        object.__setattr__(self, "_refs", Names(tuple(refs)))
        object.__setattr__(self, "_produced", Names(tuple(produced)))
        object.__setattr__(self, "_produced_refs", Names(tuple(produced_refs)))
        object.__setattr__(self, "_leaves", Names(tuple(leaves)) if leaves is not None else None)
        object.__setattr__(self, "_primary", Text(primary_ref) if primary_ref else None)
        object.__setattr__(self, "_quoted", Names(tuple(quote_marks)))
        object.__setattr__(self, "_slice_names", Names(tuple(slice_names)))

    def source(self) -> Text:
        return self._source

    def head(self) -> Text | None:
        return self._head

    def container(self) -> Text | None:
        return self._container

    def scalars(self) -> Names:
        return self._scalars

    def refs(self) -> Names:
        return self._refs

    def produced(self) -> Names:
        return self._produced

    def produced_refs(self) -> Names:
        return self._produced_refs

    def leaves(self) -> Names | None:
        return self._leaves

    def primary(self) -> Text | None:
        return self._primary

    def quoted(self) -> Names:
        return self._quoted

    def slice_names(self) -> Names:
        return self._slice_names


class AnnotationPolicySpec(ts.Spec):

    def __init__(
        self,
        blocks: tuple[str, ...],
        primitives: tuple[str, ...],
        enums: tuple[str, ...],
        scope: ScopeSpec,
        registry: RegistrySpec,
    ) -> None:
        self.blocks = blocks
        self.primitives = primitives
        self.enums = enums
        self.scope = scope
        self.registry = registry


class AnnotationPolicy(ts.ValueObject):

    _blocks: Names
    _primitives: Names
    _enums: Names
    _scope: Scope
    _registry: Registry

    def __init__(self, spec: AnnotationPolicySpec) -> None:
        object.__setattr__(self, "_blocks", Names(spec.blocks))
        object.__setattr__(self, "_primitives", Names(spec.primitives))
        object.__setattr__(self, "_enums", Names(spec.enums))
        object.__setattr__(self, "_scope", Scope(spec.scope))
        object.__setattr__(self, "_registry", Registry(spec.registry))

    def disallowed(self, annotation: Annotation) -> Names:
        leaves = annotation.leaves()
        if leaves is None:
            return Names((str(annotation.source()),))
        rejected: list[str] = []
        for leaf in leaves:
            if "." not in leaf and (leaf in self._enums or leaf in self._primitives):
                continue
            symbol = self._scope.resolve(Text(leaf))
            if symbol is None:
                rejected.append(leaf)
                continue
            if symbol in self._registry.domain_enums():
                continue
            block = self._registry.kinds().block_of(symbol)
            if block is None or str(block) not in self._blocks:
                rejected.append(leaf)
        return Names(tuple(rejected))


class SlotSpec(ts.Spec):

    def __init__(
        self,
        name: str,
        block: str | None,
        touched: tuple[str, ...],
        symbol: SymbolSpec | None = None,
    ) -> None:
        self.name = name
        self.block = block
        self.touched = touched
        self.symbol = symbol


class Slot(ts.ValueObject):

    _name: Text
    _block: Text | None
    _touched: tuple[Text, ...]
    _symbol: Symbol | None

    def __init__(self, spec: SlotSpec) -> None:
        object.__setattr__(self, "_name", Text(spec.name))
        object.__setattr__(self, "_block", Text(spec.block) if spec.block else None)
        object.__setattr__(self, "_touched", tuple(Text(block) for block in spec.touched))
        object.__setattr__(self, "_symbol", Symbol(spec.symbol) if spec.symbol is not None else None)

    def symbol(self) -> Symbol | None:
        return self._symbol

    def name(self) -> Text:
        return self._name

    def block(self) -> Text | None:
        return self._block

    def touched(self) -> tuple[Text, ...]:
        return self._touched


class SignatureSpec(ts.Spec):

    def __init__(
        self,
        where: str,
        path: str,
        lineno: int,
        name: str,
        open: tuple[str, ...],
        params: tuple[SlotSpec, ...],
        returns: SlotSpec | None,
    ) -> None:
        self.where = where
        self.path = path
        self.lineno = lineno
        self.name = name
        self.open = open
        self.params = params
        self.returns = returns


class Signature(ts.ValueObject):

    _where: Text
    _path: Path
    _lineno: Line
    _name: Text
    _open: Names
    _params: tuple[Slot, ...]
    _returns: Slot | None

    def __init__(self, spec: SignatureSpec) -> None:
        object.__setattr__(self, "_where", Text(spec.where))
        object.__setattr__(self, "_path", Path(spec.path))
        object.__setattr__(self, "_lineno", Line(spec.lineno))
        object.__setattr__(self, "_name", Text(spec.name))
        object.__setattr__(self, "_open", Names(spec.open))
        object.__setattr__(self, "_params", tuple(Slot(item) for item in spec.params))
        object.__setattr__(self, "_returns", Slot(spec.returns) if spec.returns is not None else None)

    def where(self) -> Text:
        return self._where

    def path(self) -> Path:
        return self._path

    def lineno(self) -> Line:
        return self._lineno

    def name(self) -> Text:
        return self._name

    def open(self) -> Names:
        return self._open

    def params(self) -> tuple[Slot, ...]:
        return self._params

    def returns(self) -> Slot | None:
        return self._returns


class SignaturePolicySpec(ts.Spec):

    def __init__(
        self,
        param_block: str,
        return_block: str | None,
        subject: str,
        code: str,
        taking: str,
        leading_context: bool = False,
        constructs: str = "",
    ) -> None:
        self.param_block = param_block
        self.return_block = return_block
        self.subject = subject
        self.code = code
        self.taking = taking
        self.leading_context = leading_context
        self.constructs = constructs


class SignaturePolicy(ts.ValueObject):

    _param_block: Text
    _return_block: Text | None
    _subject: Text
    _code: Code
    _taking: Text
    _leading_context: Names
    _constructs: Text | None

    def __init__(self, spec: SignaturePolicySpec) -> None:
        object.__setattr__(self, "_param_block", Text(spec.param_block))
        object.__setattr__(self, "_return_block", Text(spec.return_block) if spec.return_block else None)
        object.__setattr__(self, "_subject", Text(spec.subject))
        object.__setattr__(self, "_code", Code(spec.code))
        object.__setattr__(self, "_taking", Text(spec.taking))
        object.__setattr__(self, "_leading_context", Names(("leading",) if spec.leading_context else ()))
        object.__setattr__(self, "_constructs", Text(spec.constructs) if spec.constructs else None)

    def violations(self, signature: Signature) -> tuple[Violation, ...]:
        param_block = str(self._param_block)
        return_block = str(self._return_block) if self._return_block is not None else None
        subject = str(self._subject)
        code = str(self._code)
        taking = str(self._taking)
        where = str(signature.where())
        path = str(signature.path())
        line = int(signature.lineno())
        expected = TS_NAME_BY_BLOCK[param_block]
        found: list[Violation] = []
        params = list(signature.params())
        if self._leading_context and params and str(params[0].block()) == JOB_CONTEXT_BLOCK:
            params = params[1:]
        for slot in params:
            if str(slot.block()) == JOB_CONTEXT_BLOCK:
                arg = str(slot.name())
                found.append(
                    Violation(ViolationSpec(
                        path,
                        line,
                        "TB081",
                        f"{where} parameter {arg!r} is a ts.JobContext; a job context "
                        "is threaded as the leading parameter of an action port call and "
                        "nowhere else",
                    ))
                )
        returns = signature.returns()
        if returns is not None and str(returns.block()) == JOB_CONTEXT_BLOCK:
            found.append(
                Violation(ViolationSpec(
                    path,
                    line,
                    "TB081",
                    f"{where} returns a ts.JobContext; a job context is threaded as the "
                    "leading parameter of an action port call and nowhere else",
                ))
            )
        if signature.open():
            found.append(
                Violation(ViolationSpec(
                    path,
                    line,
                    code,
                    f"{where} uses *args/**kwargs; {taking}",
                ))
            )
        if len(params) != 1:
            found.append(
                Violation(ViolationSpec(
                    path,
                    line,
                    code,
                    f"{where} takes {len(params)} parameters; {taking}",
                ))
            )
        for slot in params:
            if str(slot.block()) != param_block:
                arg = str(slot.name())
                found.append(
                    Violation(ViolationSpec(
                        path,
                        line,
                        code,
                        f"{where} parameter {arg!r} is not a {expected}; {taking}",
                    ))
                )
        if return_block is not None and (
            returns is None or str(returns.block()) != return_block
        ):
            found.append(
                Violation(ViolationSpec(
                    path,
                    line,
                    code,
                    f"{where} does not return a {TS_NAME_BY_BLOCK[return_block]}; "
                    f"{subject} returns a {TS_NAME_BY_BLOCK[return_block]}",
                ))
            )
        return tuple(found)

    def missing_constructor_violations(self, decl: "ClassDecl") -> tuple[Violation, ...]:
        constructs = str(self._constructs) if self._constructs is not None else ""
        if decl.constructor() is not None:
            return ()
        return (
            Violation(ViolationSpec(
                str(decl.path()),
                int(decl.lineno()),
                "TB080",
                f"{decl.module()}.{decl.name()} defines no __init__; "
                f"{constructs} constructs from exactly one ts.Spec",
            )),
        )


class RecordSignaturePolicySpec(ts.Spec):

    def __init__(self, subject: str, leading_context: bool) -> None:
        self.subject = subject
        self.leading_context = leading_context


class RecordSignaturePolicy(ts.ValueObject):

    _subject: Text
    _leading_context: Names

    def __init__(self, spec: RecordSignaturePolicySpec) -> None:
        object.__setattr__(self, "_subject", Text(spec.subject))
        object.__setattr__(self, "_leading_context", Names(("leading",) if spec.leading_context else ()))

    def violations(self, decl: "ClassDecl") -> tuple[Violation, ...]:
        subject = str(self._subject)
        found: list[Violation] = []
        for signature in decl.signatures():
            where = str(signature.where())
            path = str(signature.path())
            line = int(signature.lineno())
            taken = list(signature.params())
            for slot in taken[1:] if self._leading_context else taken:
                if str(slot.block()) == JOB_CONTEXT_BLOCK:
                    arg = str(slot.name())
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB081",
                            f"{where} parameter {arg!r} is a ts.JobContext; a job "
                            "context is threaded as the leading parameter of an action "
                            "port call and nowhere else",
                        ))
                    )
            returns = signature.returns()
            if returns is not None and str(returns.block()) == JOB_CONTEXT_BLOCK:
                found.append(
                    Violation(ViolationSpec(
                        path,
                        line,
                        "TB081",
                        f"{where} returns a ts.JobContext; a job context is threaded as "
                        "the leading parameter of an action port call and nowhere else",
                    ))
                )
            slots = list(signature.params())
            if returns is not None:
                slots.append(returns)
            for slot in slots:
                touched: str | None = None
                for block in slot.touched():
                    if str(block) in DOMAIN_OBJECT_BLOCKS:
                        touched = str(block)
                        break
                if touched is not None:
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB081",
                            f"{where} carries {KIND_NAME[touched]} in its signature; "
                            f"{subject} speaks records, never domain objects",
                        ))
                    )
        return tuple(found)


class FactSpec(ts.Spec):

    def __init__(self, lineno: int, kind: str, detail: str | None, traits: tuple[str, ...]) -> None:
        self.lineno = lineno
        self.kind = kind
        self.detail = detail
        self.traits = traits


class Fact(ts.ValueObject):

    _lineno: Line
    _kind: Text
    _detail: Text | None
    _traits: Names

    def __init__(self, spec: FactSpec) -> None:
        object.__setattr__(self, "_lineno", Line(spec.lineno))
        object.__setattr__(self, "_kind", Text(spec.kind))
        object.__setattr__(self, "_detail", Text(spec.detail) if spec.detail else None)
        object.__setattr__(self, "_traits", Names(spec.traits))

    def lineno(self) -> Line:
        return self._lineno

    def kind(self) -> Text:
        return self._kind

    def detail(self) -> Text | None:
        return self._detail

    def traits(self) -> Names:
        return self._traits


class BodySpec(ts.Spec):

    def __init__(  # tesser:debt TB080
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        where: str,
        path: str,
        class_methods: tuple[str, ...],
        held_ports: tuple[str, ...],
        held_contexts: tuple[str, ...],
        signature: SignatureSpec,
        scope: ScopeSpec,
        registry: RegistrySpec,
    ) -> None:
        self.node = node
        self.where = where
        self.path = path
        self.class_methods = class_methods
        self.held_ports = held_ports
        self.held_contexts = held_contexts
        self.signature = signature
        self.scope = scope
        self.registry = registry


class Body(ts.ValueObject):

    _where: Text
    _path: Path
    _lineno: Line
    _name: Text
    _signature: Signature
    _facts: tuple[Fact, ...]

    def __init__(self, spec: BodySpec) -> None:
        fn = spec.node
        scope = Scope(spec.scope)
        registry = Registry(spec.registry)
        kinds = registry.kinds()
        class_methods = frozenset(spec.class_methods)
        functions = scope.functions()
        held_ports = frozenset(spec.held_ports)
        held_contexts = frozenset(spec.held_contexts)
        facts: list[tuple[int, str, str | None, tuple[str, ...]]] = []

        def ref_of(node: ast.expr) -> str | None:
            cursor = node
            while isinstance(cursor, ast.Subscript):
                cursor = cursor.value
            if isinstance(cursor, ast.Name):
                return cursor.id
            if isinstance(cursor, ast.Attribute) and isinstance(cursor.value, (ast.Name, ast.Attribute)):
                return f"{ast.unparse(cursor.value)}.{cursor.attr}"
            return None

        def block_of(node: ast.expr | None) -> str | None:
            if node is None:
                return None
            ref = ref_of(node)
            if ref is None:
                return None
            symbol = scope.resolve(Text(ref))
            if symbol is None:
                return None
            block = kinds.block_of(symbol)
            return str(block) if block is not None else None

        def symbol_of(node: ast.expr) -> Symbol | None:
            ref = ref_of(node)
            return scope.resolve(Text(ref)) if ref is not None else None

        def own_scope(root: ast.AST) -> typing.Iterator[ast.AST]:
            stack: list[ast.AST] = list(ast.iter_child_nodes(root))
            while stack:
                node = stack.pop()
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                    continue
                yield node
                stack.extend(ast.iter_child_nodes(node))

        def bindings() -> tuple[dict[str, list[ast.expr]], frozenset[str]]:
            values: dict[str, list[ast.expr]] = {}
            args = fn.args
            otherwise: set[str] = {arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs}
            if args.vararg is not None:
                otherwise.add(args.vararg.arg)
            if args.kwarg is not None:
                otherwise.add(args.kwarg.arg)
            for node in own_scope(fn):
                targets: list[ast.expr] = []
                value: ast.expr | None = None
                if isinstance(node, ast.Assign):
                    targets, value = list(node.targets), node.value
                elif isinstance(node, ast.AnnAssign):
                    if node.value is None:
                        continue
                    targets, value = [node.target], node.value
                elif isinstance(node, (ast.AugAssign, ast.NamedExpr)):
                    targets, value = [node.target], node.value
                elif isinstance(node, ast.comprehension):
                    continue
                elif isinstance(node, (ast.For, ast.AsyncFor)):
                    otherwise.update(sub.id for sub in ast.walk(node.target) if isinstance(sub, ast.Name))
                    continue
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if item.optional_vars is not None:
                            otherwise.update(
                                sub.id for sub in ast.walk(item.optional_vars) if isinstance(sub, ast.Name)
                            )
                    continue
                elif isinstance(node, ast.ExceptHandler):
                    if node.name is not None:
                        otherwise.add(node.name)
                    continue
                elif isinstance(node, (ast.MatchAs, ast.MatchStar)):
                    if node.name is not None:
                        otherwise.add(node.name)
                    continue
                elif isinstance(node, ast.MatchMapping):
                    if node.rest is not None:
                        otherwise.add(node.rest)
                    continue
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    otherwise.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
                    continue
                elif isinstance(node, (ast.Global, ast.Nonlocal)):
                    otherwise.update(node.names)
                    continue
                if len(targets) == 1 and isinstance(targets[0], ast.Name) and value is not None:
                    values.setdefault(targets[0].id, []).append(value)
                    continue
                for target in targets:
                    otherwise.update(sub.id for sub in ast.walk(target) if isinstance(sub, ast.Name))
            return values, frozenset(otherwise)

        def domain_kind(node: ast.expr) -> tuple[str, str] | None:
            if not isinstance(node, ast.Call):
                return None
            symbol = symbol_of(node.func)
            if symbol is None:
                return None
            block = kinds.block_of(symbol)
            if block is None or str(block) not in DOMAIN_BLOCKS:
                return None
            return (str(symbol.module()), str(symbol.name()))

        values, otherwise = bindings()
        domain_names: dict[str, tuple[str, str]] = {}
        for name, bound in values.items():
            if name in otherwise:
                continue
            found_kinds = [domain_kind(value) for value in bound]
            first = found_kinds[0]
            if first is not None and all(kind == first for kind in found_kinds):
                domain_names[name] = first

        def answers_an_outcome(node: ast.expr) -> bool:
            if isinstance(node, ast.Await):
                node = node.value
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                return False
            receiver = node.func.value
            owner: tuple[str, str] | None = None
            if isinstance(receiver, ast.Name):
                owner = domain_names.get(receiver.id)
            if owner is None:
                owner = domain_kind(receiver)
            if owner is None:
                return False
            return f"{owner[0]}|{owner[1]}|{node.func.attr}" in registry.outcome_methods()

        outcome_names = frozenset(
            name
            for name, bound in values.items()
            if name not in otherwise and all(answers_an_outcome(value) for value in bound)
        )

        def outcome_key(node: ast.expr) -> bool:
            if not isinstance(node, ast.Attribute):
                return False
            return block_of(node.value) == OUTCOME_BLOCK

        def is_comparison_call(func: ast.expr) -> bool:
            if isinstance(func, ast.Attribute):
                if func.attr in COMPARISON_CALLS:
                    return True
                if isinstance(func.value, ast.Name):
                    package = scope.package_of(Text(func.value.id))
                    return package is not None and str(package) == OPERATOR_MODULE and func.attr in OPERATOR_COMPARISONS
                return False
            if isinstance(func, ast.Name):
                origin = scope.import_of(Text(func.id))
                return (
                    origin is not None
                    and str(origin.module()) == OPERATOR_MODULE
                    and str(origin.name()) in OPERATOR_COMPARISONS
                )
            return False

        def is_truth_builtin(func: ast.expr) -> bool:
            return isinstance(func, ast.Name) and func.id in TRUTH_BUILTINS and func.id not in scope.locals()

        positional = list(fn.args.args)
        request = positional[1].arg if len(positional) >= 2 else None
        for stmt in fn.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if not isinstance(stmt.value, (ast.Name, ast.Attribute)):
                continue
            if any(isinstance(node, ast.Call) for node in ast.walk(stmt.value)):
                continue
            facts.append((stmt.lineno, "accessor", None, ()))
        decided: set[int] = set()
        matches: list[ast.Match] = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                callee = node.func
                if (
                    isinstance(callee, ast.Attribute)
                    and isinstance(callee.value, ast.Name)
                    and callee.value.id == "self"
                    and callee.attr in class_methods
                ):
                    facts.append((node.lineno, "delegation", callee.attr, ("self",)))
                elif isinstance(callee, ast.Name) and callee.id in functions:
                    facts.append((node.lineno, "delegation", callee.id, ("function",)))
                for value in list(node.args) + [kw.value for kw in node.keywords]:
                    if isinstance(value, ast.Call) and block_of(value.func) is None:
                        facts.append((value.lineno, "computed", None, ()))
                if (
                    isinstance(callee, ast.Attribute)
                    and isinstance(callee.value, ast.Attribute)
                    and isinstance(callee.value.value, ast.Name)
                    and callee.value.value.id == "self"
                ):
                    holder = callee.value.attr
                    if holder in held_ports:
                        leading = node.args[0] if node.args else None
                        threaded = (
                            isinstance(leading, ast.Attribute)
                            and isinstance(leading.value, ast.Name)
                            and leading.value.id == "self"
                            and leading.attr in held_contexts
                        )
                        facts.append((node.lineno, "port_call", holder, ("threaded",) if threaded else ()))
                    if request is not None:
                        for passed in list(node.args) + [keyword.value for keyword in node.keywords]:
                            if isinstance(passed, ast.Name) and passed.id == request:
                                facts.append((passed.lineno, "request", None, ()))
                        for inner in ast.walk(node):
                            if not isinstance(inner, ast.Attribute):
                                continue
                            current: ast.expr = inner
                            while isinstance(current, ast.Attribute):
                                current = current.value
                            if isinstance(current, ast.Name) and current.id == request:
                                facts.append((inner.lineno, "request_field", inner.attr, ()))
            if isinstance(node, (ast.If, ast.While)) and not (
                isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True
            ):
                decided.update(id(sub) for sub in ast.walk(node.test))
                facts.append((node.lineno, "branch", "if" if isinstance(node, ast.If) else "while", ()))
            elif isinstance(node, ast.Match):
                matches.append(node)
            elif isinstance(node, ast.IfExp):
                decided.update(id(sub) for sub in ast.walk(node.test))
            elif isinstance(node, ast.comprehension) and node.ifs:
                decided.update(id(sub) for test in node.ifs for sub in ast.walk(test))
        for node in ast.walk(fn):
            if id(node) in decided:
                continue
            if isinstance(node, ast.Compare):
                facts.append((node.lineno, "decision", "compare", ()))
            elif isinstance(node, ast.Call) and is_comparison_call(node.func):
                facts.append((node.lineno, "decision", "comparison_call", ()))
            elif isinstance(node, ast.Call) and is_truth_builtin(node.func):
                facts.append((node.lineno, "decision", "truth", ()))
            elif isinstance(node, ast.IfExp):
                facts.append((node.lineno, "decision", "ifexp", ()))
            elif isinstance(node, ast.BoolOp):
                facts.append((node.lineno, "decision", "boolop", ()))
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                facts.append((node.lineno, "decision", "not", ()))
            elif isinstance(node, ast.comprehension) and node.ifs:
                facts.append((node.ifs[0].lineno, "decision", "filter", ()))
        matches.sort(key=lambda node: node.lineno)
        for node in matches:
            traits: list[str] = []
            subject = node.subject
            answered = subject.id in outcome_names if isinstance(subject, ast.Name) else answers_an_outcome(subject)
            if answered:
                traits.append("answers")
            if any(
                outcome_key(sub.value)
                for case in node.cases
                for sub in ast.walk(case.pattern)
                if isinstance(sub, ast.MatchValue)
            ):
                traits.append("members")
            facts.append((node.lineno, "match", None, tuple(traits)))
        handed = {
            arg.arg
            for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
            if arg.arg != "self" and block_of(arg.annotation) == JOB_CONTEXT_BLOCK
        }
        if handed:
            for node in ast.walk(fn):
                if isinstance(node, ast.AnnAssign):
                    targets: list[ast.expr] = [node.target]
                    assigned: ast.expr | None = node.value
                elif isinstance(node, ast.Assign):
                    targets = list(node.targets)
                    assigned = node.value
                else:
                    continue
                if not (isinstance(assigned, ast.Name) and assigned.id in handed):
                    continue
                for target in targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                        facts.append((node.lineno, "keeps_context", target.attr, ()))
        object.__setattr__(self, "_where", Text(spec.where))
        object.__setattr__(self, "_path", Path(spec.path))
        object.__setattr__(self, "_lineno", Line(fn.lineno))
        object.__setattr__(self, "_name", Text(fn.name))
        object.__setattr__(self, "_signature", Signature(spec.signature))
        object.__setattr__(self, "_facts", tuple(Fact(FactSpec(*item)) for item in facts))

    def name(self) -> Text:
        return self._name

    def signature(self) -> Signature:
        return self._signature

    def delegation_violations(self) -> tuple[Violation, ...]:
        where = str(self._where)
        found: list[Violation] = []
        for fact in self._facts:
            if str(fact.kind()) != "delegation":
                continue
            if "self" in fact.traits():
                delegate = str(fact.detail())
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(fact.lineno()),
                        "TB082",
                        f"{where} delegates to self.{delegate}; a service inlines its logic",
                    ))
                )
            else:
                function = str(fact.detail())
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(fact.lineno()),
                        "TB082",
                        f"{where} delegates to {function}; a service inlines its logic",
                    ))
                )
        return tuple(found)

    def violations(self) -> tuple[Violation, ...]:
        where = str(self._where)
        path = str(self._path)
        found: list[Violation] = []
        first_match = True
        for fact in self._facts:
            kind = str(fact.kind())
            line = int(fact.lineno())
            if kind == "request":
                found.append(
                    Violation(ViolationSpec(
                        path,
                        line,
                        "TB082",
                        f"{where} sends its request itself straight to a port; "
                        "a value crossing into a port has passed through a domain type",
                    ))
                )
            elif kind == "request_field":
                field = str(fact.detail())
                found.append(
                    Violation(ViolationSpec(
                        path,
                        line,
                        "TB082",
                        f"{where} sends {field} from its request straight to a port; "
                        "a value crossing into a port has passed through a domain type",
                    ))
                )
            elif kind == "accessor":
                found.append(
                    Violation(ViolationSpec(
                        path,
                        line,
                        "TB082",
                        f"{where} names a straight accessor; a service method names what it "
                        "computes, and reads an accessor where it is used",
                    ))
                )
            elif kind == "computed":
                found.append(
                    Violation(ViolationSpec(
                        path,
                        line,
                        "TB082",
                        f"{where} computes in an argument; a service method names what it "
                        "computes in a local, and passes a name, a reader, or a declared kind",
                    ))
                )
            elif kind == "branch":
                keyword = str(fact.detail())
                found.append(
                    Violation(ViolationSpec(
                        path,
                        line,
                        "TB082",
                        f"{where} branches with {keyword}; a service method branches only by "
                        "matching an outcome — `while True:` ended by a match arm is the loop — "
                        "because a truth test on a domain object is a bool the domain never handed out",
                    ))
                )
            elif kind == "decision":
                decision = str(fact.detail())
                if decision == "compare":
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} compares two values; a service method asks a domain object "
                            "and never compares, because a comparison is a rule written down "
                            "beside the object that should own it",
                        ))
                    )
                elif decision == "comparison_call":
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} calls a comparison; a service method asks a domain object "
                            "and never compares, because a comparison is a rule written down "
                            "beside the object that should own it",
                        ))
                    )
                elif decision == "truth":
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} asks a builtin whether values are true; a service method "
                            "branches only by matching an outcome, because bool, any, and all "
                            "read a truth the domain never handed out",
                        ))
                    )
                elif decision == "ifexp":
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} chooses with a conditional expression; a service method "
                            "branches only by matching an outcome, because `x if c else y` is a "
                            "branch with no arms for a member added later",
                        ))
                    )
                elif decision == "boolop":
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} joins conditions with and/or; a service method branches "
                            "only by matching an outcome, because a boolean operator is a rule "
                            "assembled from values the domain never handed out",
                        ))
                    )
                elif decision == "not":
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} negates a value; a service method branches only by matching "
                            "an outcome, because `not x` is a truth test on a value the domain "
                            "never handed out",
                        ))
                    )
                elif decision == "filter":
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} filters a comprehension; a service method branches only by "
                            "matching an outcome, because which items belong is a rule the "
                            "domain collection should own",
                        ))
                    )
            elif kind == "match":
                if not first_match:
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} matches a second time; a service method decides once, because "
                            "a second decision in one method is a rule about their order that no "
                            "domain object owns",
                        ))
                    )
                first_match = False
                if "answers" not in fact.traits():
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB082",
                            f"{where} match subject is not a call on a domain object; "
                            "a service method matches the outcome a domain object handed "
                            "back, because a port answer, a string, or an attribute is a "
                            "rule the service would be reading for itself",
                        ))
                    )
                elif "members" not in fact.traits():
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            line,
                            "TB084",
                            f"{where} matches a domain call whose arms name no outcome "
                            "member; a match on what a domain object answered names outcome "
                            "members and closes on assert_never, because string arms hide a "
                            "member added later from the type checker",
                        ))
                    )
        return tuple(found)

    def port_call_violations(self) -> tuple[Violation, ...]:
        where = str(self._where)
        calls = [fact for fact in self._facts if str(fact.kind()) == "port_call"]
        if len(calls) == 1:
            return ()
        return (
            Violation(ViolationSpec(
                str(self._path),
                int(self._lineno),
                "TB082",
                f"{where} makes {len(calls)} calls on its port; "
                "an action makes exactly one call on its port",
            )),
        )

    def thread_violations(self) -> tuple[Violation, ...]:
        where = str(self._where)
        found: list[Violation] = []
        for fact in self._facts:
            if str(fact.kind()) != "port_call" or "threaded" in fact.traits():
                continue
            published = str(fact.detail())
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(fact.lineno()),
                    "TB082",
                    f"{where} calls {published} without its job context first; "
                    "an orchestrator threads its job context into every action port call",
                ))
            )
        return tuple(found)

    def held_context_violations(self) -> tuple[Violation, ...]:
        owner = str(self._where).rsplit(".", 1)[0]
        found: list[Violation] = []
        for fact in self._facts:
            if str(fact.kind()) != "keeps_context":
                continue
            published = str(fact.detail())
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(fact.lineno()),
                    "TB081",
                    f"{owner} keeps {published}, a job "
                    "context; an adapter is built once and never holds an "
                    "invocation's job context",
                ))
            )
        return tuple(found)


class DependencyPolicySpec(ts.Spec):

    def __init__(self, subject: str, context_ok: bool = False) -> None:
        self.subject = subject
        self.context_ok = context_ok


class DependencyPolicy(ts.ValueObject):

    _subject: Text
    _context_ok: Names

    def __init__(self, spec: DependencyPolicySpec) -> None:
        object.__setattr__(self, "_subject", Text(spec.subject))
        object.__setattr__(self, "_context_ok", Names(("context",) if spec.context_ok else ()))

    def violations(self, signature: Signature) -> tuple[Violation, ...]:
        subject = str(self._subject)
        where = str(signature.where())
        found: list[Violation] = []
        for slot in signature.params():
            block = str(slot.block()) if slot.block() is not None else None
            if self._context_ok and block == JOB_CONTEXT_BLOCK:
                continue
            if block not in ("port", "store"):
                arg = str(slot.name())
                found.append(
                    Violation(ViolationSpec(
                        str(signature.path()),
                        int(signature.lineno()),
                        "TB081",
                        f"{where} parameter {arg!r} is not a ts.Port or a ts.Store; "
                        f"{subject} depends only on ports and the stores that yield them",
                    ))
                )
        return tuple(found)


class FieldSpec(ts.Spec):

    def __init__(self, name: str, node: ast.expr, lineno: int) -> None:  # tesser:debt TB080
        self.name = name
        self.node = node
        self.lineno = lineno


class Field(ts.ValueObject):

    _name: Text
    _annotation: Annotation
    _lineno: Line

    def __init__(self, spec: FieldSpec) -> None:
        object.__setattr__(self, "_name", Text(spec.name))
        object.__setattr__(self, "_annotation", Annotation(spec.node))
        object.__setattr__(self, "_lineno", Line(spec.lineno))

    def name(self) -> Text:
        return self._name

    def annotation(self) -> Annotation:
        return self._annotation

    def lineno(self) -> Line:
        return self._lineno


class ParamSpec(ts.Spec):

    def __init__(self, name: str, node: ast.expr | None, lineno: int) -> None:  # tesser:debt TB080
        self.name = name
        self.node = node
        self.lineno = lineno


class Param(ts.ValueObject):

    _name: Text
    _annotation: Annotation | None
    _lineno: Line

    def __init__(self, spec: ParamSpec) -> None:
        object.__setattr__(self, "_name", Text(spec.name))
        object.__setattr__(self, "_annotation", Annotation(spec.node) if spec.node is not None else None)
        object.__setattr__(self, "_lineno", Line(spec.lineno))

    def name(self) -> Text:
        return self._name

    def annotation(self) -> Annotation | None:
        return self._annotation

    def lineno(self) -> Line:
        return self._lineno


class MethodSpec(ts.Spec):

    def __init__(self, node: ast.FunctionDef | ast.AsyncFunctionDef, owner: str) -> None:  # tesser:debt TB080
        self.node = node
        self.owner = owner


class Method(ts.Entity):

    _identity: Text
    _name: Text
    _lineno: Line
    _decorators: Names
    _returns: Annotation | None
    _params: tuple[Param, ...]
    _open: Names
    _bare_self_attr: Text | None
    _delegated: Text | None
    _constructs: Names
    _form: Names

    def __init__(self, spec: MethodSpec) -> None:
        node = spec.node
        shape_only = all(
            isinstance(stmt, ast.Pass)
            or (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis)
            for stmt in node.body
        )
        object.__setattr__(self, "_form", Names(("shape",) if shape_only else ()))
        object.__setattr__(self, "_identity", Text(f"{spec.owner}.{node.name}"))
        object.__setattr__(self, "_name", Text(node.name))
        object.__setattr__(self, "_lineno", Line(node.lineno))
        decorators: set[str] = set()
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(target, ast.Name):
                decorators.add(target.id)
        object.__setattr__(self, "_decorators", Names(tuple(decorators)))
        object.__setattr__(
            self, "_returns", Annotation(node.returns) if node.returns is not None else None
        )
        positional = list(node.args.posonlyargs) + list(node.args.args)
        if positional and positional[0].arg in ("self", "cls"):
            positional = positional[1:]
        object.__setattr__(
            self,
            "_params",
            tuple(
                Param(ParamSpec(arg.arg, arg.annotation, arg.lineno))
                for arg in positional + list(node.args.kwonlyargs)
            ),
        )
        opened: list[str] = []
        if node.args.vararg is not None:
            opened.append("*args")
        if node.args.kwarg is not None:
            opened.append("**kwargs")
        object.__setattr__(self, "_open", Names(tuple(opened)))
        bare = node.body[0].value if len(node.body) == 1 and isinstance(node.body[0], ast.Return) else None
        bare_self_attr: str | None = None
        delegated: str | None = None
        if isinstance(bare, ast.Attribute) and isinstance(bare.value, ast.Name) and bare.value.id == "self":
            bare_self_attr = bare.attr
        if isinstance(bare, ast.Call) and len(bare.args) == 1:
            delegated = (
                bare.func.id
                if isinstance(bare.func, ast.Name)
                else bare.func.attr
                if isinstance(bare.func, ast.Attribute)
                else None
            )
            if not (
                isinstance(bare.args[0], ast.Attribute)
                and isinstance(bare.args[0].value, ast.Name)
                and bare.args[0].value.id == "self"
            ):
                delegated = None
        object.__setattr__(self, "_bare_self_attr", Text(bare_self_attr) if bare_self_attr else None)
        object.__setattr__(self, "_delegated", Text(delegated) if delegated else None)
        object.__setattr__(
            self,
            "_constructs",
            Names(tuple(
                call.func.id
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id in ("cls", spec.owner)
            )),
        )

    @property
    def identity(self) -> Text:
        return self._identity

    def name(self) -> Text:
        return self._name

    def lineno(self) -> Line:
        return self._lineno

    def decorators(self) -> Names:
        return self._decorators

    def returns(self) -> Annotation | None:
        return self._returns

    def params(self) -> tuple[Param, ...]:
        return self._params

    def open(self) -> Names:
        return self._open

    def bare_self_attr(self) -> Text | None:
        return self._bare_self_attr

    def delegated(self) -> Text | None:
        return self._delegated

    def constructs(self) -> Names:
        return self._constructs

    def form(self) -> Names:
        return self._form


class ClassDeclSpec(ts.Spec):

    def __init__(  # tesser:debt TB080
        self,
        node: ast.ClassDef,
        module: str,
        path: str,
        scope: ScopeSpec,
        registry: RegistrySpec,
    ) -> None:
        self.node = node
        self.module = module
        self.path = path
        self.scope = scope
        self.registry = registry


class ClassDecl(ts.Entity):

    _identity: Text
    _module: Text
    _path: Path
    _name: Text
    _lineno: Line
    _scope: Scope
    _registry: Registry
    _parameter_policy: AnnotationPolicy
    _fields: tuple[Field, ...]
    _methods: tuple[Method, ...]
    _signatures: tuple[Signature, ...]
    _bodies: tuple[Body, ...]
    _held_ports: Names
    _held_contexts: Names
    _stores: tuple[Fact, ...]
    _self_annotations: tuple[Field, ...]
    _bases: Names
    _decoration: Names
    _extras: tuple[Fact, ...]
    _leaf: Text | None

    def __init__(self, spec: ClassDeclSpec) -> None:
        node = spec.node
        object.__setattr__(self, "_identity", Text(f"{spec.module}.{node.name}"))
        object.__setattr__(self, "_module", Text(spec.module))
        object.__setattr__(self, "_path", Path(spec.path))
        object.__setattr__(self, "_name", Text(node.name))
        object.__setattr__(self, "_lineno", Line(node.lineno))
        object.__setattr__(self, "_scope", Scope(spec.scope))
        object.__setattr__(self, "_registry", Registry(spec.registry))
        object.__setattr__(
            self,
            "_parameter_policy",
            AnnotationPolicy(AnnotationPolicySpec(
                tuple(DOMAIN_METHOD_PARAMETER_BLOCKS),
                tuple(DOMAIN_METHOD_PRIMITIVES),
                (),
                spec.scope,
                spec.registry,
            )),
        )
        fields: list[Field] = []
        methods: list[Method] = []
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields.append(Field(FieldSpec(stmt.target.id, stmt.annotation, stmt.lineno)))
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(Method(MethodSpec(stmt, node.name)))
        object.__setattr__(self, "_fields", tuple(fields))
        object.__setattr__(self, "_methods", tuple(methods))
        scope = self._scope
        kinds = self._registry.kinds()

        SlotRow = tuple[str, str | None, tuple[str, ...], tuple[str, str] | None]

        def slot(name: str, annotation: Annotation | None, unquote: bool) -> SlotRow:
            if annotation is None:
                return (name, None, (), None)
            block: str | None = None
            resolved: Symbol | None = None
            primary = annotation.primary()
            if primary is not None and (unquote or not annotation.quoted()):
                resolved = scope.resolve(primary)
                block_text = kinds.block_of(resolved) if resolved is not None else None
                block = str(block_text) if block_text is not None else None
            touched: list[str] = []
            for symbol in scope.symbols(annotation):
                named = kinds.block_of(symbol)
                if named is not None:
                    touched.append(str(named))
            return (
                name,
                block,
                tuple(touched),
                (str(resolved.module()), str(resolved.name())) if resolved is not None else None,
            )

        SignatureRow = tuple[str, str, int, str, tuple[str, ...], tuple[SlotRow, ...], SlotRow | None]

        def slot_spec(row: SlotRow) -> SlotSpec:
            symbol = row[3]
            return SlotSpec(row[0], row[1], row[2], SymbolSpec(symbol[0], symbol[1]) if symbol is not None else None)

        def signature_spec(row: SignatureRow) -> SignatureSpec:
            return SignatureSpec(
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                tuple(slot_spec(item) for item in row[5]),
                slot_spec(row[6]) if row[6] is not None else None,
            )

        signature_rows: list[SignatureRow] = []
        for method in methods:
            signature_rows.append((
                f"{spec.module}.{node.name}.{method.name()}",
                spec.path,
                int(method.lineno()),
                str(method.name()),
                tuple(method.open()),
                tuple(slot(str(param.name()), param.annotation(), True) for param in method.params()),
                slot("return", method.returns(), False) if method.returns() is not None else None,
            ))
        object.__setattr__(self, "_signatures", tuple(Signature(signature_spec(row)) for row in signature_rows))
        own_block = kinds.block_of(Symbol(SymbolSpec(spec.module, node.name)))
        init_node = next(
            (
                item
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"
            ),
            None,
        )

        def held(kind: str) -> tuple[str, ...]:
            if init_node is None:
                return ()
            named: set[str] = set()
            for arg in init_node.args.posonlyargs + init_node.args.args + init_node.args.kwonlyargs:
                if arg.arg == "self" or arg.annotation is None:
                    continue
                primary = Annotation(arg.annotation).primary()
                resolved = scope.resolve(primary) if primary is not None else None
                block = kinds.block_of(resolved) if resolved is not None else None
                if block is not None and str(block) == kind:
                    named.add(arg.arg)
            kept: set[str] = set()
            for inner in ast.walk(init_node):
                if isinstance(inner, ast.AnnAssign):
                    targets: list[ast.expr] = [inner.target]
                    value: ast.expr | None = inner.value
                elif isinstance(inner, ast.Assign):
                    targets = list(inner.targets)
                    value = inner.value
                else:
                    continue
                if not (isinstance(value, ast.Name) and value.id in named):
                    continue
                for target in targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                        kept.add(target.attr)
            return tuple(sorted(kept))

        held_ports = held("port")
        held_contexts = held(JOB_CONTEXT_BLOCK)
        object.__setattr__(self, "_held_ports", Names(held_ports))
        object.__setattr__(self, "_held_contexts", Names(held_contexts))
        stores: list[tuple[int, str, str | None, tuple[str, ...]]] = []
        for inner in ast.walk(node):
            if isinstance(inner, ast.AnnAssign):
                store_targets: list[ast.expr] = [inner.target]
            elif isinstance(inner, ast.Assign):
                store_targets = list(inner.targets)
            elif isinstance(inner, ast.AugAssign):
                store_targets = [inner.target]
            else:
                continue
            for target in store_targets:
                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
                    stores.append((inner.lineno, "store", target.attr, ()))
        object.__setattr__(self, "_stores", tuple(Fact(FactSpec(*item)) for item in stores))
        self_annotations: list[Field] = []
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.AnnAssign)
                and isinstance(inner.target, ast.Attribute)
                and isinstance(inner.target.value, ast.Name)
                and inner.target.value.id == "self"
            ):
                self_annotations.append(Field(FieldSpec(inner.target.attr, inner.annotation, inner.lineno)))
        object.__setattr__(self, "_self_annotations", tuple(self_annotations))
        bases: list[str] = []
        for base in node.bases:
            base_ref = Annotation(base).primary()
            base_symbol = scope.resolve(base_ref) if base_ref is not None else None
            bases.append(f"{base_symbol.module()}|{base_symbol.name()}" if base_symbol is not None else "?")
        object.__setattr__(self, "_bases", Names(tuple(f"{index}:{item}" for index, item in enumerate(bases))))
        decoration: list[str] = []
        if node.decorator_list:
            decoration.append("decorated")
        if node.keywords:
            decoration.append("keyworded")
        object.__setattr__(self, "_decoration", Names(tuple(decoration)))

        def is_enum_auto(value: ast.expr) -> bool:
            if not isinstance(value, ast.Call) or value.args or value.keywords:
                return False
            if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name):
                package = scope.package_of(Text(value.func.value.id))
                return package is not None and str(package) == ENUM_MODULE and value.func.attr == "auto"
            if isinstance(value.func, ast.Name):
                origin = scope.import_of(Text(value.func.id))
                return origin is not None and str(origin.module()) == ENUM_MODULE and str(origin.name()) == "auto"
            return False

        extras: list[tuple[int, str, str | None, tuple[str, ...]]] = []
        for item in node.body:
            if isinstance(item, ast.Pass):
                continue
            member_target: ast.expr | None = None
            member_value: ast.expr | None = None
            if isinstance(item, ast.AnnAssign):
                member_target, member_value = item.target, item.value
            elif isinstance(item, ast.Assign) and len(item.targets) == 1:
                member_target, member_value = item.targets[0], item.value
            is_member = (
                isinstance(member_target, ast.Name)
                and not member_target.id.startswith("_")
                and not (isinstance(item, ast.AnnAssign) and not isinstance(item.annotation, ast.Name))
                and (
                    isinstance(member_value, ast.Constant)
                    or (
                        isinstance(member_value, ast.UnaryOp)
                        and isinstance(member_value.operand, ast.Constant)
                        and isinstance(member_value.operand.value, (int, float))
                    )
                    or (member_value is not None and is_enum_auto(member_value))
                )
            )
            if not is_member:
                extras.append((item.lineno, "extra", None, ()))
            valued = (
                isinstance(item, ast.Assign) and len(item.targets) == 1 and not is_enum_auto(item.value)
            ) or (
                isinstance(item, ast.AnnAssign) and item.value is not None and not is_enum_auto(item.value)
            )
            if valued:
                extras.append((item.lineno, "valued", None, ()))
        object.__setattr__(self, "_extras", tuple(Fact(FactSpec(*item)) for item in extras))
        bodies: list[Body] = []
        if own_block is not None and str(own_block) in BODY_BLOCKS:
            class_methods = tuple(str(method.name()) for method in methods)
            for item, row in zip(
                (stmt for stmt in node.body if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))),
                signature_rows,
            ):
                bodies.append(Body(BodySpec(
                    item,
                    row[0],
                    spec.path,
                    class_methods,
                    held_ports,
                    held_contexts,
                    signature_spec(row),
                    spec.scope,
                    spec.registry,
                )))
        object.__setattr__(self, "_bodies", tuple(bodies))
        stored = [field for field in fields if str(field.annotation().head()) != "ClassVar"]
        leaf: str | None = None
        if len(stored) == 1:
            head = str(stored[0].annotation().head())
            if head in WRAPPABLE_SCALARS or head in NON_WRAPPABLE_SCALARS:
                leaf = head
        object.__setattr__(self, "_leaf", Text(leaf) if leaf else None)

    @property
    def identity(self) -> Text:
        return self._identity

    def module(self) -> Text:
        return self._module

    def path(self) -> Path:
        return self._path

    def name(self) -> Text:
        return self._name

    def lineno(self) -> Line:
        return self._lineno

    def signatures(self) -> tuple[Signature, ...]:
        return self._signatures

    def constructor(self) -> Signature | None:
        for signature in self._signatures:
            if str(signature.name()) == "__init__":
                return signature
        return None

    def bodies(self) -> tuple[Body, ...]:
        return self._bodies

    def port_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        declared = self._scope.classes()
        kinds = self._registry.kinds()
        for method in self._methods:
            where = f"{self._module}.{self._name}.{method.name()}"
            if not method.form():
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB051",
                        f"{where} carries a body; a port method declares a shape and "
                        "never a body, because a ports module holds no logic to import",
                    ))
                )
            if str(method.name()).startswith("_") and str(method.name()) != "__call__":
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB081",
                        f"{where} is not a call an implementer provides; a port declares "
                        "only its public calls and __call__, because a private name is "
                        "not private to anyone implementing or holding the port",
                    ))
                )
                continue
            annotations = [param.annotation() for param in method.params()] + [method.returns()]
            for annotation in annotations:
                if annotation is not None and "." not in str(annotation.source()) and str(annotation.source()) in declared:
                    continue
                primary = annotation.primary() if annotation is not None else None
                symbol = self._scope.resolve(primary) if primary is not None else None
                block = kinds.block_of(symbol) if symbol is not None else None
                if block is not None and str(block) == JOB_CONTEXT_BLOCK:
                    continue
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB081",
                        f"{where} names a shape it does not declare; a port method speaks "
                        "requests and responses declared in its own ports module, never a "
                        "bare ts.Request or ts.Response, which two ports would share",
                    ))
                )
        return tuple(found)

    def store_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        kinds = self._registry.kinds()
        ports = Names(tuple(
            name
            for name in self._scope.classes()
            if str(kinds.block_of(Symbol(SymbolSpec(str(self._module), name)))) == "port"
        ))
        for method in self._methods:
            where = f"{self._module}.{self._name}.{method.name()}"
            if not method.form():
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB051",
                        f"{where} carries a body; a port method declares a shape and "
                        "never a body, because a ports module holds no logic to import",
                    ))
                )
            if str(method.name()) != STORE_METHOD:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB081",
                        f"{where} is not transaction; a store declares exactly one "
                        "method, which opens a transaction and yields the repository "
                        "bound to it",
                    ))
                )
                continue
            params = method.params()
            if params:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB081",
                        f"{where} takes {len(params)} parameters; a store's transaction "
                        "takes none, because the transaction is the only thing it opens",
                    ))
                )
            returns = method.returns()
            yields_port = (
                returns is not None
                and str(returns.head()) == STORE_RETURN
                and returns.primary() is not None
                and "." in str(returns.primary())
                and len(tuple(returns.slice_names())) == 1
                and all(name in ports for name in returns.slice_names())
            )
            if not yields_port:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB081",
                        f"{where} does not return an AsyncContextManager of a port declared "
                        "beside it; a store's transaction hands back the repository bound to "
                        "it, which is the one port its own module declares",
                    ))
                )
        if not any(str(method.name()) == STORE_METHOD for method in self._methods):
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(self._lineno),
                    "TB081",
                    f"{self._module}.{self._name} declares no transaction; a store "
                    "declares exactly one method, which opens a transaction and yields "
                    "the repository bound to it",
                ))
            )
        return tuple(found)

    def actions_client_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        spoken = self._scope.spoken()
        for method in self._methods:
            where = f"{self._module}.{self._name}.{method.name()}"
            if not method.form():
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB051",
                        f"{where} carries a body; an application client method declares "
                        "a shape and never a body, because a job imports it for the shape",
                    ))
                )
            if str(method.name()).startswith("_") and str(method.name()) != "__call__":
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB081",
                        f"{where} is not a call a job may make; an application client "
                        "declares only its public calls and __call__",
                    ))
                )
                continue
            annotations = [param.annotation() for param in method.params()] + [method.returns()]
            for annotation in annotations:
                primary = annotation.primary() if annotation is not None else None
                symbol = self._scope.resolve(primary) if primary is not None else None
                if symbol is not None and spoken is not None and symbol.module() == spoken:
                    continue
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB081",
                        f"{where} names a shape its ports module does not declare; an "
                        "application client speaks the requests and responses of the "
                        "ports module it imports",
                    ))
                )
        return tuple(found)

    def component_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        kinds = self._registry.kinds()
        if not any(str(method.name()) == "close" for method in self._methods):
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(self._lineno),
                    "TB081",
                    f"{self._module}.{self._name} defines no close; "
                    "a component releases what it constructed",
                ))
            )
        annotated: dict[str, Annotation] = {str(field.name()): field.annotation() for field in self._fields}
        for field in self._self_annotations:
            annotated[str(field.name())] = field.annotation()
        for fact in self._stores:
            published = str(fact.detail())
            if published.startswith("_"):
                continue
            if published not in ("client", "jobs"):
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(fact.lineno()),
                        "TB081",
                        f"{self._module}.{self._name} publishes {published}; "
                        "a component publishes only its client and its jobs",
                    ))
                )
                continue
            expected = "client" if published == "client" else "job"
            annotation = annotated.get(published)
            primary = annotation.primary() if annotation is not None else None
            symbol = self._scope.resolve(primary) if primary is not None else None
            block = kinds.block_of(symbol) if symbol is not None else None
            named = block is not None and str(block) == expected
            if not named and expected == "job" and annotation is not None and str(annotation.head()) == "tuple":
                elements = list(annotation.slice_names())
                named = bool(elements) and all(
                    element != "?" and (
                        lambda resolved: resolved is not None and str(kinds.block_of(resolved)) == "job"
                    )(self._scope.resolve(Text(element)))
                    for element in elements
                )
            if not named:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(fact.lineno()),
                        "TB081",
                        f"{self._module}.{self._name} publishes {published} untyped; "
                        "a component publishes only its client and its jobs",
                    ))
                )
        return tuple(found)

    def outcome_violations(self) -> tuple[Violation, ...]:
        where = f"{self._module}.{self._name}"
        found: list[Violation] = []
        bases = list(self._bases)
        if len(bases) > 1:
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(self._lineno),
                    "TB084",
                    f"{where} mixes another base into its outcome; an outcome subclasses "
                    "ts.Outcome alone, because a mixed-in base gives its members a value "
                    "to compare against outside a match",
                ))
            )
        elif bases and bases[0] != f"0:{OUTCOME_BASE[0]}|{OUTCOME_BASE[1]}":
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(self._lineno),
                    "TB084",
                    f"{where} subclasses another outcome; an outcome subclasses ts.Outcome "
                    "directly, because a hierarchy reopens the closed set",
                ))
            )
        if self._decoration:
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(self._lineno),
                    "TB084",
                    f"{where} is decorated or keyworded; an outcome is a bare class statement, "
                    "because a decorator or a metaclass rewrites the closed set into a home for behavior",
                ))
            )
        for fact in self._extras:
            if str(fact.kind()) == "extra":
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(fact.lineno()),
                        "TB084",
                        f"{where} carries more than its members; an outcome is a closed set of "
                        "names and nothing else, because behavior belongs on the object that returns it",
                    ))
                )
            elif str(fact.kind()) == "valued":
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(fact.lineno()),
                        "TB084",
                        f"{where} gives a member a value; an outcome member is enum.auto(), "
                        "because an outcome is matched, never serialized",
                    ))
                )
        return tuple(found)

    def actions_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        init = next((item for item in self._signatures if str(item.name()) == "__init__"), None)
        if init is None:
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(self._lineno),
                    "TB081",
                    f"{self._module}.{self._name} defines no __init__; "
                    "a class of actions takes exactly one port",
                ))
            )
            return tuple(found)
        params = init.params()
        if len(params) != 1:
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(init.lineno()),
                    "TB081",
                    f"{self._module}.{self._name}.__init__ takes {len(params)} parameters; "
                    "a class of actions takes exactly one port",
                ))
            )
        return tuple(found)

    def orchestrator_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        init = next((item for item in self._signatures if str(item.name()) == "__init__"), None)
        if init is None:
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(self._lineno),
                    "TB081",
                    f"{self._module}.{self._name} defines no __init__; "
                    "an orchestrator depends only on action ports — a port an "
                    "application client speaks",
                ))
            )
        else:
            where = str(init.where())
            taken = [slot for slot in init.params() if str(slot.block()) == JOB_CONTEXT_BLOCK]
            if len(taken) != 1:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(init.lineno()),
                        "TB081",
                        f"{where} takes {len(taken)} job contexts; "
                        "an orchestrator takes exactly one job context and its action ports",
                    ))
                )
            for slot in init.params():
                if str(slot.block()) != "port":
                    continue
                if slot.symbol() is not None and slot.symbol() in self._registry.action_ports():
                    continue
                arg = str(slot.name())
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(init.lineno()),
                        "TB081",
                        f"{where} parameter {arg!r} is a port no application client "
                        "speaks; an orchestrator depends only on action ports — a port "
                        "an application client speaks",
                    ))
                )
        held = self._held_ports | self._held_contexts
        for fact in self._stores:
            published = str(fact.detail())
            if published in held:
                continue
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(fact.lineno()),
                    "TB081",
                    f"{self._module}.{self._name} keeps {published}; "
                    "an orchestrator stores only its job context and its action ports",
                ))
            )
        return tuple(found)

    def vo_field_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for field in self._fields:
            if str(field.annotation().head()) in MUTABLE_COLLECTIONS:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(field.lineno()),
                        "TB002",
                        f"{self._module}.{self._name} field {field.name()} is a mutable collection; "
                        "a value object's field is hashable — a tuple or frozenset, never "
                        "a mutable collection",
                    ))
                )
        return tuple(found)

    def exposure_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        stored = [field for field in self._fields if str(field.annotation().head()) != "ClassVar"]
        by_name = {str(field.name()): field.annotation() for field in stored}
        for field in stored:
            if str(field.name()).startswith("_"):
                continue
            annotation = field.annotation()
            if annotation.scalars() & SCALAR_NAMES or self._scope.symbols(annotation) & self._registry.domain_enums():
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(field.lineno()),
                        "TB010",
                        f"{self._module}.{self._name} exposes field {field.name()}; "
                        "a value object hides its representation — a public field belongs on a spec",
                    ))
                )
        for method in self._methods:
            if str(method.name()).startswith("_") and str(method.name()) != PUBLIC_CALL:
                continue
            attr = method.bare_self_attr()
            if attr is None:
                continue
            returned = method.returns() if method.returns() is not None else by_name.get(str(attr))
            if returned is None:
                continue
            if returned.scalars() & SCALAR_NAMES or self._scope.symbols(returned) & self._registry.domain_enums():
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB010",
                        f"{self._module}.{self._name}.{method.name()} passes the raw primitive through; "
                        "a value object's accessor returns a value object — "
                        "the canonical exit is the only primitive exit",
                    ))
                )
        return tuple(found)

    def composition_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        stored = [field for field in self._fields if str(field.annotation().head()) != "ClassVar"]
        for field in stored:
            head = str(field.annotation().head())
            if head in NON_WRAPPABLE_SCALARS:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(field.lineno()),
                        "TB016",
                        f"{self._module}.{self._name} field {field.name()} is a {head}; "
                        "bool and complex are not value-object material — "
                        "model the raw value or reach for an enum",
                    ))
                )
        if len(stored) >= 2:
            for field in stored:
                if field.annotation().scalars() & WRAPPABLE_NAMES:
                    found.append(
                        Violation(ViolationSpec(
                            str(self._path),
                            int(field.lineno()),
                            "TB016",
                            f"{self._module}.{self._name} field {field.name()} is a bare primitive; "
                            "a compound backs itself with child value objects",
                        ))
                    )
        return tuple(found)

    def construction_path_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for method in self._methods:
            if not method.decorators() & CONSTRUCTOR_DECORATORS:
                continue
            returns = method.returns()
            produced = returns.produced() if returns is not None else Names(())
            second_path = bool(produced & Names((str(self._name), "Self")))
            if not produced and method.constructs():
                second_path = True
            if second_path:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB017",
                        f"{self._module}.{self._name}.{method.name()} is a second construction path; "
                        "a value object has one construction path — its own __init__",
                    ))
                )
        return tuple(found)

    def exit_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        conversions = [method for method in self._methods if str(method.name()) in CONVERSION_DUNDERS]
        leaf = str(self._leaf) if self._leaf is not None else None
        if leaf is not None and leaf in WRAPPABLE_SCALARS:
            expected = CANONICAL_EXIT[leaf]
            helper = CANONICAL_HELPER.get(leaf)
            for method in conversions:
                delegated = method.delegated()
                if str(method.name()) != expected:
                    found.append(
                        Violation(ViolationSpec(
                            str(self._path),
                            int(method.lineno()),
                            "TB015",
                            f"{self._module}.{self._name}.{method.name()} is a mismatched exit; "
                            "a leaf defines exactly its backing type's conversion dunder",
                        ))
                    )
                elif helper is not None and (delegated is None or str(delegated) != helper):
                    found.append(
                        Violation(ViolationSpec(
                            str(self._path),
                            int(method.lineno()),
                            "TB018",
                            f"{self._module}.{self._name}.{method.name()} hand-rolls its exit; "
                            "a canonical exit is a one-line delegation to its canonical_* policy",
                        ))
                    )
            return tuple(found)
        for method in conversions:
            found.append(
                Violation(ViolationSpec(
                    str(self._path),
                    int(method.lineno()),
                    "TB015",
                    f"{self._module}.{self._name}.{method.name()} is a primitive exit; "
                    "a structured domain object has no primitive exit — "
                    "decompose through leaf components",
                ))
            )
        return tuple(found)

    def structured_exit_violations(self) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                str(self._path),
                int(method.lineno()),
                "TB015",
                f"{self._module}.{self._name}.{method.name()} is a primitive exit; "
                "a structured domain object has no primitive exit — "
                "decompose through leaf components",
            ))
            for method in self._methods
            if str(method.name()) in CONVERSION_DUNDERS
        )

    def copy_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        by_name = {
            str(field.name()): field.annotation()
            for field in self._fields
            if str(field.annotation().head()) != "ClassVar"
        }
        for method in self._methods:
            if str(method.name()).startswith("_"):
                continue
            attr = method.bare_self_attr()
            if attr is None:
                continue
            returns = method.returns()
            returned = returns.head() if returns is not None else None
            if returned is None and str(attr) in by_name:
                returned = by_name[str(attr)].head()
            if returned is not None and str(returned) in MUTABLE_COLLECTIONS:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB011",
                        f"{self._module}.{self._name}.{method.name()} hands back its backing collection; "
                        "an accessor returns a defensive copy, never the backing store",
                    ))
                )
        return tuple(found)

    def held_root_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for field in self._fields:
            if str(field.annotation().head()) == "ClassVar":
                continue
            for symbol in self._scope.symbols(field.annotation()):
                if symbol.name() == self._name:
                    continue
                if str(self._registry.kinds().block_of(symbol)) == "aggregate":
                    found.append(
                        Violation(ViolationSpec(
                            str(self._path),
                            int(field.lineno()),
                            "TB012",
                            f"{self._module}.{self._name} field {field.name()} holds another aggregate root; "
                            "an aggregate is referenced by its ID value object, never held",
                        ))
                    )
        return tuple(found)

    def outcome_field_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for field in self._fields:
            if str(field.annotation().head()) == "ClassVar":
                continue
            for symbol in self._scope.symbols(field.annotation()):
                if str(self._registry.kinds().block_of(symbol)) == OUTCOME_BLOCK:
                    found.append(
                        Violation(ViolationSpec(
                            str(self._path),
                            int(field.lineno()),
                            "TB084",
                            f"{self._module}.{self._name} field {field.name()} holds an outcome; "
                            "an outcome is returned and matched, never held — "
                            "what must be kept is state, on a spec with an exit",
                        ))
                    )
                    break
        return tuple(found)

    def domain_method_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for method in self._methods:
            name = str(method.name())
            if name in LANGUAGE_FIXED:
                continue
            if name.startswith("_") and name not in COMPARISON_DUNDERS and name != PUBLIC_CALL:
                continue
            where = f"{self._module}.{self._name}.{method.name()}"
            returns = method.returns()
            if returns is None:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB019",
                        f"{where} return is unannotated; a domain object's method names what it "
                        "hands back, because a caller reading an unnamed return is guessing at "
                        "the answer the object gave",
                    ))
                )
            params = method.params()
            if method.open():
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB019",
                        f"{where} uses *args/**kwargs; a domain object's method names the one "
                        "thing it takes, because an open argument list is a signature no rule can read",
                    ))
                )
            if len(params) > 1:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB019",
                        f"{where} takes {len(params)} parameters; a domain object's method takes "
                        "one thing, because a rule about how two arguments relate belongs inside "
                        "the object that owns them",
                    ))
                )
            for param in params:
                arg = str(param.name())
                annotation = param.annotation()
                if annotation is None:
                    found.append(
                        Violation(ViolationSpec(
                            str(self._path),
                            int(method.lineno()),
                            "TB019",
                            f"{where} parameter {arg!r} is unannotated; a domain object's "
                            "method names the one thing it takes, because an argument with no "
                            "type is a signature no rule can read",
                        ))
                    )
                    continue
                if annotation.container() is not None:
                    found.append(
                        Violation(ViolationSpec(
                            str(self._path),
                            int(method.lineno()),
                            "TB019",
                            f"{where} parameter {arg!r} is a container; a domain object's "
                            "method takes one primitive, one spec, or one domain object, because "
                            "a collection handed in is a type the domain has not named",
                        ))
                    )
                    continue
                if self._parameter_policy.disallowed(annotation):
                    found.append(
                        Violation(ViolationSpec(
                            str(self._path),
                            int(method.lineno()),
                            "TB019",
                            f"{where} parameter {arg!r} is not a primitive, a spec, or a "
                            "domain object; a domain object's method takes one of those three, "
                            "because a port or client shape reaching a domain method is the wire "
                            "format deciding what the domain may be asked",
                        ))
                    )
            if returns is None or str(returns.source()) == "None":
                continue
            if method.bare_self_attr() is not None:
                continue
            spec_return = False
            offenders: list[str] = []
            for ref in returns.produced_refs():
                produced_name = ref.rsplit(".", 1)[-1]
                if produced_name in RETURN_SKIPPED or produced_name == str(self._name):
                    continue
                symbol = self._scope.resolve(Text(ref))
                block = self._registry.kinds().block_of(symbol) if symbol is not None else None
                if str(block) == "spec":
                    spec_return = True
                    continue
                if block is not None and str(block) in DOMAIN_OBJECT_BLOCKS:
                    continue
                offenders.append(produced_name)
            if spec_return:
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB015",
                        f"{self._module}.{self._name}.{method.name()} returns a spec; "
                        "a domain object never serializes itself — "
                        "a spec is construction data, not an exit",
                    ))
                )
            if offenders:
                named = ", ".join(sorted(set(offenders)))
                found.append(
                    Violation(ViolationSpec(
                        str(self._path),
                        int(method.lineno()),
                        "TB019",
                        f"{self._module}.{self._name}.{method.name()} returns {named}; "
                        "a domain object's public behavior hands back domain objects — "
                        "the licensed exits are the protocol dunders, the canonical exit, "
                        "and a -> None transition",
                    ))
                )
        return tuple(found)


AGGREGATE_CONSTRUCTOR: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "spec", None, "a domain constructor", "TB080", "a domain constructor takes exactly one ts.Spec", constructs="an aggregate"
))

ENTITY_CONSTRUCTOR: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "spec", None, "a domain constructor", "TB080", "a domain constructor takes exactly one ts.Spec", constructs="an entity"
))

APP_CONFIG_CONSTRUCTOR: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "app_spec", None, "a config constructor", "TB080", "a config constructor takes exactly one ts.Spec", constructs="a config"
))

COMPONENT_CONFIG_CONSTRUCTOR: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "component_spec", None, "a config constructor", "TB080", "a config constructor takes exactly one ts.Spec", constructs="a config"
))

CLIENT_METHOD: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "request", "response", "a client method", "TB081", "a client method takes exactly one ts.Request"
))

SERVICE_METHOD: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "request", "response", "a service method", "TB081", "a service method takes exactly one ts.Request"
))

ACTIONS_METHOD: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "port_request", "port_response", "an actions method", "TB081", "an actions method takes exactly one ts.Request"
))

ORCHESTRATOR_METHOD: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "port_request", "port_response", "an orchestrator method", "TB081", "an orchestrator method takes exactly one ts.Request"
))

SERVICE_DEPENDENCIES: typing.Final[DependencyPolicy] = DependencyPolicy(DependencyPolicySpec("a service"))

ACTIONS_DEPENDENCIES: typing.Final[DependencyPolicy] = DependencyPolicy(DependencyPolicySpec("a class of actions"))

ORCHESTRATOR_DEPENDENCIES: typing.Final[DependencyPolicy] = DependencyPolicy(DependencyPolicySpec("an orchestrator", True))

ADAPTER_RECORDS: typing.Final[RecordSignaturePolicy] = RecordSignaturePolicy(RecordSignaturePolicySpec("an adapter", True))

HANDLER_RECORDS: typing.Final[RecordSignaturePolicy] = RecordSignaturePolicy(RecordSignaturePolicySpec("an adapter", False))

PORT_RECORDS: typing.Final[RecordSignaturePolicy] = RecordSignaturePolicy(RecordSignaturePolicySpec("a port", True))

PORT_METHOD: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "port_request",
    "port_response",
    "a port method",
    "TB081",
    "a port method takes one ts.Request, which a leading ts.JobContext may precede",
    True,
))

APP_CLIENT_METHOD: typing.Final[SignaturePolicy] = SignaturePolicy(SignaturePolicySpec(
    "port_request", "port_response", "an application client method", "TB081", "an application client method takes exactly one ts.Request"
))


class ModuleSpec(ts.Spec):

    def __init__(self, path: str, name: str, source: str, is_package: bool, tops: tuple[str, ...] = ()) -> None:
        self.path = path
        self.name = name
        self.source = source
        self.is_package = is_package
        self.tops = tops


class Module(ts.Entity):

    def __init__(self, spec: ModuleSpec) -> None:
        if not spec.name:
            raise ValueError("module name must be non-empty")
        if not spec.path:
            raise ValueError("module path must be non-empty")
        tree = ast.parse(spec.source)
        self._path = spec.path
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(spec.source).readline))
        except (tokenize.TokenError, IndentationError):
            tokens = []
        self._comments = tuple(
            Comment(CommentSpec(line=token.start[0], text=token.string))
            for token in tokens
            if token.type == tokenize.COMMENT
        )
        debts: list[Debt] = []
        for comment in self._comments:
            text = str(comment._text).lstrip("#").strip()
            if text.startswith(DEBT_FILE_MARKER):
                rest = text[len(DEBT_FILE_MARKER) :]
                file_level = True
            elif text.startswith(DEBT_MARKER):
                rest = text[len(DEBT_MARKER) :]
                file_level = False
            else:
                continue
            if rest and rest[0] not in " \t":
                continue
            codes = tuple(part for part in rest.replace(",", " ").split() if part)
            if any(not CODE_SHAPE.match(code) for code in codes):
                debts.append(
                    Debt(DebtSpec(
                        line=int(comment._line),
                        codes=(),
                        file_level=file_level,
                        form="malformed",
                    ))
                )
                continue
            debts.append(
                Debt(DebtSpec(line=int(comment._line), codes=codes, file_level=file_level))
            )
        self._debts = tuple(debts)
        self._name = spec.name
        self._is_package = spec.is_package
        parts = spec.name.split(".")
        self._package: tuple[str, ...] = tuple(parts if spec.is_package else parts[:-1])
        self._body: tuple[ast.stmt, ...] = tuple(tree.body)
        self._package_aliases: dict[str, str] = {}
        self._imported: dict[str, tuple[str, str]] = {}
        self._classes: dict[str, ast.ClassDef] = {}
        self._calls: tuple[ast.Call, ...] = tuple(
            node for node in ast.walk(tree) if isinstance(node, ast.Call)
        )
        self._subscripts: tuple[ast.Subscript, ...] = tuple(
            node for node in ast.walk(tree) if isinstance(node, ast.Subscript)
        )
        self._assignments: tuple[ast.Assign | ast.AnnAssign, ...] = tuple(
            node for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.AnnAssign))
        )
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
                                TesserImport(TesserImportSpec(
                                    alias.name,
                                    node.lineno,
                                    alias.asname == "ts",
                                    False,
                                    alias.asname is None,
                                ))
                            )
                        else:
                            nested_tesser.append((alias.name, node.lineno))
                    if id(node) in top_level:
                        self._package_aliases[alias.asname or alias.name] = alias.name
                    edges.append(
                        ImportEdge(ImportEdgeSpec(alias.name, node.lineno, False, alias.asname is not None, spec.path, spec.name))
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.level > len(self._package):
                    dots = "." * node.level
                    broken_relatives.append((dots + (node.module or ""), node.lineno))
                    continue
                base = (
                    ()
                    if node.level == 0
                    else self._package[: max(0, len(self._package) - (node.level - 1))]
                )
                if node.module is None:
                    for alias in node.names:
                        target = ".".join(base + (alias.name,))
                        if id(node) in top_level:
                            self._package_aliases[alias.asname or alias.name] = target
                        edges.append(ImportEdge(ImportEdgeSpec(target, node.lineno, True, False, spec.path, spec.name)))
                    continue
                target = ".".join(base + (node.module,))
                for alias in node.names:
                    if id(node) in top_level:
                        self._imported[alias.asname or alias.name] = (target, alias.name)
                edges.append(ImportEdge(ImportEdgeSpec(target, node.lineno, True, False, spec.path, spec.name)))
                if target.split(".")[0] == TESSER:
                    if id(node) in top_level:
                        tesser_imports.append(TesserImport(TesserImportSpec(target, node.lineno, False, True)))
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


        spoken_modules = [
            str(edge._target)
            for edge in self._edges
            if str(edge._target).split(".")[0] in spec.tops
            and str(edge._target).split(".")[1:3] == [PORTS_PARENT_ROLE, PORTS_PACKAGE]
        ]
        self._spoken: str | None = spoken_modules[0] if len(spoken_modules) == 1 else None
        self._scope = Scope(ScopeSpec(
            self._name,
            tuple(ImportSpec(local, target, original) for local, (target, original) in self._imported.items()),
            tuple(AliasSpec(alias, package) for alias, package in self._package_aliases.items()),
            tuple(self._classes),
            tuple(sorted(self._functions)),
            self._spoken,
        ))

    def spoken(self) -> Text | None:
        return Text(self._spoken) if self._spoken else None

    def outcome_use_violations(self, registry: RegistrySpec) -> tuple[Violation, ...]:
        module_name = self._name
        path = self._path
        kinds = Registry(registry).kinds()
        scope = self._scope

        def resolve(node: ast.expr) -> tuple[str, str] | None:
            cursor = node
            while isinstance(cursor, ast.Subscript):
                cursor = cursor.value
            ref: str | None = None
            if isinstance(cursor, ast.Name):
                ref = cursor.id
            elif isinstance(cursor, ast.Attribute) and isinstance(cursor.value, (ast.Name, ast.Attribute)):
                ref = f"{ast.unparse(cursor.value)}.{cursor.attr}"
            if ref is None:
                return None
            symbol = scope.resolve(Text(ref))
            return (str(symbol.module()), str(symbol.name())) if symbol is not None else None

        def block_of(node: ast.expr) -> str | None:
            key = resolve(node)
            if key is None:
                return None
            block = kinds.block_of(Symbol(SymbolSpec(key[0], key[1])))
            return str(block) if block is not None else None

        def names_outcome(node: ast.expr) -> bool:
            stack: list[ast.expr] = [node]
            while stack:
                top = stack.pop()
                for sub in ast.walk(top):
                    if isinstance(sub, (ast.Name, ast.Attribute)):
                        if block_of(sub) == OUTCOME_BLOCK:
                            return True
                    elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        try:
                            quoted = ast.parse(sub.value, mode="eval").body
                        except SyntaxError:
                            continue
                        if not isinstance(quoted, ast.Constant):
                            stack.append(quoted)
            return False

        def outcome_key(node: ast.expr) -> tuple[str, str] | None:
            if not isinstance(node, ast.Attribute):
                return None
            key = resolve(node.value)
            if key is None or block_of(node.value) != OUTCOME_BLOCK:
                return None
            return key

        def is_member_pattern(pattern: ast.pattern) -> bool:
            if isinstance(pattern, ast.MatchOr):
                return all(is_member_pattern(alternative) for alternative in pattern.patterns)
            return isinstance(pattern, ast.MatchValue) and outcome_key(pattern.value) is not None

        def returned(node: ast.expr) -> typing.Iterator[ast.expr]:
            yield node
            if isinstance(node, ast.IfExp):
                yield from returned(node.body)
                yield from returned(node.orelse)
            elif isinstance(node, ast.Tuple):
                for element in node.elts:
                    yield from returned(element)
            elif isinstance(node, ast.BoolOp):
                for value in node.values:
                    yield from returned(value)

        def closes_with_assert_never(node: ast.Match) -> bool:
            last = node.cases[-1]
            pattern = last.pattern
            if last.guard is not None:
                return False
            if not (isinstance(pattern, ast.MatchAs) and pattern.name is not None):
                return False
            wildcard = pattern.pattern
            if wildcard is not None and not (
                isinstance(wildcard, ast.MatchAs) and wildcard.pattern is None and wildcard.name is None
            ):
                return False
            if len(last.body) != 1 or not isinstance(last.body[0], (ast.Expr, ast.Return)):
                return False
            call = last.body[0].value
            if not (isinstance(call, ast.Call) and len(call.args) == 1 and not call.keywords):
                return False
            if not (isinstance(call.args[0], ast.Name) and call.args[0].id == pattern.name):
                return False
            callee = call.func
            rebound = {
                target.id
                for assignment in self._assignments
                for target in (
                    assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
                )
                if isinstance(target, ast.Name)
            }
            if isinstance(callee, ast.Attribute) and isinstance(callee.value, ast.Name):
                package = scope.package_of(Text(callee.value.id))
                return (
                    package is not None
                    and str(package) == TYPING_MODULE
                    and callee.attr == ASSERT_NEVER
                    and callee.value.id not in rebound
                )
            if isinstance(callee, ast.Name):
                origin = scope.import_of(Text(callee.id))
                return (
                    origin is not None
                    and str(origin.module()) == TYPING_MODULE
                    and str(origin.name()) == ASSERT_NEVER
                    and callee.id not in rebound
                )
            return False

        found: list[Violation] = []
        matched: set[int] = set()
        attributes: list[ast.Attribute] = []
        names: list[ast.expr] = []
        annotated: set[int] = set()
        for node in (sub for stmt in self._body for sub in ast.walk(stmt)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                extras = [arg for arg in (node.args.vararg, node.args.kwarg) if arg is not None]
                for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs + extras:
                    if arg.annotation is None:
                        continue
                    annotated.update(id(sub) for sub in ast.walk(arg.annotation))
                    if names_outcome(arg.annotation):
                        taker = node.name
                        found.append(
                            Violation(ViolationSpec(
                                path,
                                node.lineno,
                                "TB084",
                                f"{module_name}.{taker} takes an outcome; an outcome is returned "
                                "and matched, never passed on, because it lives between the return "
                                "and the match",
                            ))
                        )
                if node.returns is not None:
                    annotated.update(id(sub) for sub in ast.walk(node.returns))
            elif isinstance(node, ast.AnnAssign):
                annotated.update(id(sub) for sub in ast.walk(node.annotation))
                if isinstance(node.target, ast.Attribute) and names_outcome(node.annotation):
                    kept = ast.unparse(node.target)
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            node.lineno,
                            "TB084",
                            f"{module_name} keeps an outcome on {kept}; "
                            "an outcome is returned and matched, never kept, because what must "
                            "be kept is state, on a spec with an exit",
                        ))
                    )
            elif isinstance(node, ast.ClassDef):
                annotated.update(id(sub) for base in node.bases for sub in ast.walk(base))
                own = frozenset(
                    item.name
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.returns is not None
                    and names_outcome(item.returns)
                )
                carriers: set[str] = set()
                for assignment in ast.walk(node):
                    if not isinstance(assignment, (ast.Assign, ast.AnnAssign)):
                        continue
                    value = assignment.value
                    if value is None:
                        continue
                    produces = any(
                        isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.value.id == "self"
                        and sub.func.attr in own
                        for sub in ast.walk(value)
                    ) or any(
                        isinstance(sub, ast.Name) and sub.id in carriers for sub in ast.walk(value)
                    )
                    if not produces:
                        continue
                    targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
                    receiving: list[ast.expr] = []
                    for target in targets:
                        if (
                            isinstance(target, ast.Tuple)
                            and isinstance(value, ast.Tuple)
                            and len(target.elts) == len(value.elts)
                        ):
                            receiving.extend(
                                element
                                for element, given in zip(target.elts, value.elts)
                                if any(
                                    isinstance(sub, ast.Call)
                                    and isinstance(sub.func, ast.Attribute)
                                    and isinstance(sub.func.value, ast.Name)
                                    and sub.func.value.id == "self"
                                    and sub.func.attr in own
                                    or isinstance(sub, ast.Name) and sub.id in carriers
                                    for sub in ast.walk(given)
                                )
                            )
                        else:
                            receiving.append(target)
                    for target in receiving:
                        for leaf in ast.walk(target):
                            if isinstance(leaf, ast.Name):
                                carriers.add(leaf.id)
                    for target in receiving:
                        for leaf in ast.walk(target):
                            if not isinstance(leaf, ast.Attribute):
                                continue
                            kept = ast.unparse(leaf)
                            found.append(
                                Violation(ViolationSpec(
                                    path,
                                    assignment.lineno,
                                    "TB084",
                                    f"{module_name} keeps an outcome on {kept}; "
                                    "an outcome is returned and matched, never kept, because what must "
                                    "be kept is state, on a spec with an exit",
                                ))
                            )
            if isinstance(node, ast.Attribute):
                attributes.append(node)
                names.append(node)
                if node.attr in OUTCOME_SUNDERS:
                    sunder = node.attr
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            node.lineno,
                            "TB084",
                            f"{module_name} reads {sunder}; an outcome is matched, never read, "
                            "because its value and name are the exhaustiveness the type checker "
                            "cannot see",
                        ))
                    )
            elif isinstance(node, ast.Name):
                names.append(node)
            elif isinstance(node, ast.Return) and node.value is not None:
                matched.update(id(sub) for sub in returned(node.value))
            elif isinstance(node, ast.Match):
                outcome_match = False
                for case in node.cases:
                    for sub in ast.walk(case.pattern):
                        if isinstance(sub, ast.MatchValue) and outcome_key(sub.value) is not None:
                            outcome_match = True
                            matched.add(id(sub.value))
                if outcome_match:
                    for case in node.cases[:-1]:
                        if case.guard is None and is_member_pattern(case.pattern):
                            continue
                        found.append(
                            Violation(ViolationSpec(
                                path,
                                case.pattern.lineno,
                                "TB084",
                                f"{module_name} mixes a pattern into an outcome match; "
                                "every arm before the closer names members, because a class, "
                                "capture, or guarded arm swallows a member added later",
                            ))
                        )
                if outcome_match and not closes_with_assert_never(node):
                    found.append(
                        Violation(ViolationSpec(
                            path,
                            node.lineno,
                            "TB084",
                            f"{module_name} matches an outcome without closing on assert_never; "
                            "a match on an outcome ends in `case _ as never: assert_never(never)`, "
                            "because a member added later is otherwise a silent site",
                        ))
                    )
        member_bases: set[int] = set()
        for node in attributes:
            key = outcome_key(node)
            if key is None:
                continue
            member_bases.update(id(sub) for sub in ast.walk(node.value))
            if id(node) in matched:
                continue
            outcome = key[1]
            member = node.attr
            found.append(
                Violation(ViolationSpec(
                    path,
                    node.lineno,
                    "TB084",
                    f"{module_name} names {outcome}.{member} outside a match; "
                    "an outcome member is read only by a match, because a member compared "
                    "anywhere else is a branch the type checker cannot exhaust",
                ))
            )
        for node in names:
            if id(node) in annotated or id(node) in member_bases:
                continue
            key = resolve(node)
            if key is None or block_of(node) != OUTCOME_BLOCK:
                continue
            outcome = key[1]
            found.append(
                Violation(ViolationSpec(
                    path,
                    node.lineno,
                    "TB084",
                    f"{module_name} reaches into {outcome}; an outcome class is named only "
                    "in an annotation, a return, or a case pattern, because indexing, getattr, "
                    "and iteration read members the type checker cannot exhaust",
                ))
            )
        return tuple(found)

    def comment_violations(self) -> tuple[Violation, ...]:
        module_name = self._name
        found: list[Violation] = []
        for comment in self._comments:
            if DIRECTIVE.match(str(comment._text)):
                continue
            if int(comment._line) <= 2 and CODING_DECL.match(str(comment._text)):
                continue
            found.append(
                Violation(ViolationSpec(
                    self._path,
                    int(comment._line),
                    "TB020",
                    f"{module_name} carries a code comment; code speaks for itself — "
                    "comments, docstrings, and loose strings belong in the doc layer",
                ))
            )
        doc_ids: set[int] = set()
        body = self._body
        if body and (isinstance((body[0]), ast.Expr)
                    and isinstance((body[0]).value, ast.Constant)
                    and isinstance((body[0]).value.value, str)):
            doc_ids.add(id(body[0]))
        for stmt in body:
            for node in ast.walk(stmt):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.body and (isinstance((node.body[0]), ast.Expr)
                                and isinstance((node.body[0]).value, ast.Constant)
                                and isinstance((node.body[0]).value.value, str)):
                        doc_ids.add(id(node.body[0]))
        for stmt in body:
            for node in ast.walk(stmt):
                if not (isinstance(node, ast.Expr)
                            and isinstance(node.value, ast.Constant)
                            and isinstance(node.value.value, str)):
                    continue
                kind = "a docstring" if id(node) in doc_ids else "a bare string statement"
                found.append(
                    Violation(ViolationSpec(
                        self._path,
                        node.lineno,
                        "TB020",
                        f"{module_name} carries {kind}; code speaks for itself — "
                        "comments, docstrings, and loose strings belong in the doc layer",
                    ))
                )
        return tuple(found)

    def double_violations(self) -> tuple[Violation, ...]:
        module_name = self._name
        found: list[Violation] = []
        for stmt in self._body:
            for node in ast.walk(stmt):
                if isinstance(node, ast.ImportFrom):
                    target = node.module or ""
                    if (any(
                                target == banned or target.startswith(banned + ".") for banned in MOCK_MODULES
                            )) or (
                        target == "unittest" and any(alias.name == "mock" for alias in node.names)
                    ):
                        found.append(
                            Violation(ViolationSpec(
                                self._path,
                                node.lineno,
                                "TB030",
                                f"{module_name} imports a mocking library; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            ))
                        )
                    elif target in ("pytest", "_pytest.monkeypatch") and any(
                        alias.name == "MonkeyPatch" for alias in node.names
                    ):
                        found.append(
                            Violation(ViolationSpec(
                                self._path,
                                node.lineno,
                                "TB030",
                                f"{module_name} reaches for pytest MonkeyPatch; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            ))
                        )
                elif isinstance(node, ast.Import):
                    if any((any(
                                alias.name == banned or alias.name.startswith(banned + ".") for banned in MOCK_MODULES
                            )) for alias in node.names):
                        found.append(
                            Violation(ViolationSpec(
                                self._path,
                                node.lineno,
                                "TB030",
                                f"{module_name} imports a mocking library; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            ))
                        )
                elif isinstance(node, ast.Attribute):
                    if (
                        node.attr == "mock"
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "unittest"
                    ):
                        found.append(
                            Violation(ViolationSpec(
                                self._path,
                                node.lineno,
                                "TB030",
                                f"{module_name} imports a mocking library; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            ))
                        )
                    elif (
                        node.attr == "MonkeyPatch"
                        and isinstance(node.value, ast.Name)
                        and node.value.id == "pytest"
                    ):
                        found.append(
                            Violation(ViolationSpec(
                                self._path,
                                node.lineno,
                                "TB030",
                                f"{module_name} reaches for pytest MonkeyPatch; a test double is "
                                "a hand-written fake, never a mocking library or a runtime patcher",
                            ))
                        )
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not (
                        node.name.startswith("test_")
                        or any(
                            (
                                isinstance(target, ast.Attribute)
                                and target.attr == "fixture"
                            )
                            or (isinstance(target, ast.Name) and target.id == "fixture")
                            for target in (
                                decorator.func
                                if isinstance(decorator, ast.Call)
                                else decorator
                                for decorator in node.decorator_list
                            )
                        )
                    ):
                        continue
                    args = node.args
                    for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                        if arg.arg in PATCHER_FIXTURES:
                            found.append(
                                Violation(ViolationSpec(
                                    self._path,
                                    arg.lineno,
                                    "TB030",
                                    f"{module_name}.{node.name} takes the {arg.arg} fixture; "
                                    "a test double is a hand-written fake, never a mocking "
                                    "library or a runtime patcher",
                                ))
                            )
        return tuple(found)

    def shadowing_violations(self) -> tuple[Violation, ...]:
        module_name = self._name
        found: list[Violation] = []
        scopes: list[tuple[ast.AST | None, list[ast.AST]]] = [
            (None, [stmt for stmt in self._body])
        ]
        for stmt in self._body:
            for node in ast.walk(stmt):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    scopes.append((node, list(node.body)))
                elif isinstance(node, ast.Lambda):
                    scopes.append((node, [node.body]))
        for holder, roots in scopes:
            items: list[ast.AST] = []
            stack: list[ast.AST] = list(roots)
            while stack:
                item = stack.pop()
                if isinstance(
                    item,
                    (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
                ):
                    continue
                items.append(item)
                stack.extend(ast.iter_child_nodes(item))
            shadowed: set[str] = set()
            if isinstance(
                holder, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
            ):
                args = holder.args
                for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                    if arg.arg in BUILTIN_NAMES:
                        shadowed.add(arg.arg)
                for extra in (args.vararg, args.kwarg):
                    if extra is not None and extra.arg in BUILTIN_NAMES:
                        shadowed.add(extra.arg)
            elsewhere: set[str] = set()
            for child in items:
                if isinstance(child, (ast.Global, ast.Nonlocal)):
                    elsewhere.update(child.names)
                if (
                    isinstance(child, ast.ExceptHandler)
                    and child.name is not None
                    and child.name in BUILTIN_NAMES
                ):
                    shadowed.add(child.name)
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
                            shadowed.add(name.id)
            bound = frozenset(shadowed - elsewhere)
            if not bound:
                continue
            for child in items:
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id in bound
                ):
                    found.append(
                        Violation(ViolationSpec(
                            self._path,
                            child.lineno,
                            "TB033",
                            f"{module_name} binds {child.func.id} and calls it in the same "
                            "scope; a shadowed builtin is never called — rename the binding",
                        ))
                    )
        return tuple(found)

    def string_equality_violations(self) -> tuple[Violation, ...]:
        module_name = self._name
        found: list[Violation] = []
        for stmt in self._body:
            for node in ast.walk(stmt):
                if not isinstance(node, ast.Compare) or len(node.ops) != 1:
                    continue
                right = node.comparators[0]
                if (
                    isinstance(node.ops[0], ast.Eq)
                    and (isinstance(node.left, ast.Call) and (
                                (
                                    isinstance(node.left.func, ast.Name)
                                    and node.left.func.id == "str"
                                    and len(node.left.args) == 1
                                )
                                or (isinstance(node.left.func, ast.Attribute) and node.left.func.attr == "__str__")
                            ))
                    and (isinstance(right, ast.Call) and (
                                (
                                    isinstance(right.func, ast.Name)
                                    and right.func.id == "str"
                                    and len(right.args) == 1
                                )
                                or (isinstance(right.func, ast.Attribute) and right.func.attr == "__str__")
                            ))
                ):
                    found.append(
                        Violation(ViolationSpec(
                            self._path,
                            node.lineno,
                            "TB004",
                            f"{module_name} equates two str() calls; compare value objects "
                            "by value, never by their string form",
                        ))
                    )
        return tuple(found)

    def sibling_reference_violations(self) -> tuple[Violation, ...]:
        module_name = self._name
        def declared(body: list[ast.stmt]) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
            out: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
            stack: list[ast.AST] = list(body)
            while stack:
                cur = stack.pop()
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append(cur)
                    continue
                if isinstance(cur, (ast.ClassDef, ast.Lambda)):
                    continue
                stack.extend(ast.iter_child_nodes(cur))
            return out

        def receiver(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
            names = {d.id for d in fn.decorator_list if isinstance(d, ast.Name)}
            if "staticmethod" in names:
                return None
            args = fn.args.posonlyargs + fn.args.args
            if not args:
                return None
            return args[0].arg

        def rebinds(fn: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, name: str) -> bool:
            args = fn.args
            bound = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
            if args.vararg is not None:
                bound.add(args.vararg.arg)
            if args.kwarg is not None:
                bound.add(args.kwarg.arg)
            return name in bound

        def reads(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> list[ast.Attribute]:
            hits: list[ast.Attribute] = []
            stack: list[ast.AST] = list(ast.iter_child_nodes(fn))
            while stack:
                cur = stack.pop()
                if isinstance(cur, ast.ClassDef):
                    continue
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    if rebinds(cur, name):
                        continue
                    stack.extend(ast.iter_child_nodes(cur))
                    continue
                if isinstance(cur, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    targets = {
                        t.id
                        for comp in cur.generators
                        for t in ast.walk(comp.target)
                        if isinstance(t, ast.Name)
                    }
                    if name in targets:
                        continue
                    stack.extend(ast.iter_child_nodes(cur))
                    continue
                if (
                    isinstance(cur, ast.Attribute)
                    and isinstance(cur.ctx, ast.Load)
                    and isinstance(cur.value, ast.Name)
                    and cur.value.id == name
                ):
                    hits.append(cur)
                stack.extend(ast.iter_child_nodes(cur))
            return hits

        def recurs(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str | None) -> bool:
            if name is None:
                return False
            stack: list[ast.AST] = list(ast.iter_child_nodes(fn))
            while stack:
                cur = stack.pop()
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                    continue
                if (
                    isinstance(cur, ast.Call)
                    and isinstance(cur.func, ast.Attribute)
                    and isinstance(cur.func.value, ast.Name)
                    and cur.func.value.id == name
                    and cur.func.attr == fn.name
                ):
                    return True
                stack.extend(ast.iter_child_nodes(cur))
            return False

        found: list[Violation] = []
        for stmt in self._body:
            for node in ast.walk(stmt):
                if not isinstance(node, ast.ClassDef):
                    continue
                methods = declared(node.body)
                names = {method.name for method in methods}
                recursive = {method.name for method in methods if recurs(method, receiver(method))}
                for member in methods:
                    own = receiver(member)
                    if own is None:
                        continue
                    for inner in reads(member, own):
                        sibling = inner.attr
                        if sibling not in names:
                            continue
                        if sibling == member.name or sibling in recursive:
                            continue
                        if sibling.startswith("__") and sibling.endswith("__"):
                            continue
                        found.append(
                            Violation(ViolationSpec(
                                self._path,
                                inner.lineno,
                                "TB051",
                                f"{module_name}.{node.name}.{member.name} reaches sibling "
                                f"{sibling}; a method is for outsiders — a class reaches "
                                "into itself only for direct recursion",
                            ))
                        )
        return tuple(found)

    def dynamic_import_violations(self) -> tuple[Violation, ...]:
        module_name = self._name
        found: list[Violation] = []
        bound: set[str] = set()
        for assignment in self._assignments:
            assigned = assignment.value
            if assigned is None:
                continue
            assigned_reaches = False
            if isinstance(assigned, ast.Attribute) and isinstance(assigned.value, ast.Name):
                package = self._package_aliases.get(assigned.value.id)
                assigned_reaches = package == IMPORTLIB or (
                    package == BUILTINS and assigned.attr == BUILTIN_IMPORT
                )
            elif isinstance(assigned, ast.Name):
                origin = self._imported.get(assigned.id)
                assigned_reaches = (
                    assigned.id == BUILTIN_IMPORT
                    and assigned.id not in self._functions
                ) or (
                    origin is not None
                    and (
                        origin[0] == IMPORTLIB
                        or (origin[0] == BUILTINS and origin[1] == BUILTIN_IMPORT)
                    )
                )
            elif isinstance(assigned, ast.Call):
                assigned_reaches = (
                    isinstance(assigned.func, ast.Name)
                    and assigned.func.id == "getattr"
                    and bool(assigned.args)
                    and isinstance(assigned.args[0], ast.Name)
                    and self._package_aliases.get(assigned.args[0].id) == IMPORTLIB
                )
            if not assigned_reaches:
                continue
            targets = (
                assignment.targets
                if isinstance(assignment, ast.Assign)
                else [assignment.target]
            )
            bound.update(t.id for t in targets if isinstance(t, ast.Name))
        rebound = frozenset(bound)
        for lookup in self._subscripts:
            if (
                isinstance(lookup.value, ast.Attribute)
                and lookup.value.attr == "modules"
                and (isinstance(lookup.value.value, ast.Name)
                            and self._package_aliases.get(lookup.value.value.id) == SYS_MODULE)
            ):
                found.append(
                    Violation(ViolationSpec(
                        self._path,
                        lookup.lineno,
                        "TB068",
                        f"{module_name} imports dynamically through sys.modules; "
                        "an import is a statement the walk can read, never a call",
                    ))
                )
        for node in self._calls:
            callee = node.func
            callee_reaches = False
            if isinstance(callee, ast.Attribute) and isinstance(callee.value, ast.Name):
                package = self._package_aliases.get(callee.value.id)
                callee_reaches = package == IMPORTLIB or (
                    package == BUILTINS and callee.attr == BUILTIN_IMPORT
                )
            elif isinstance(callee, ast.Name):
                origin = self._imported.get(callee.id)
                callee_reaches = (
                    callee.id == BUILTIN_IMPORT
                    and callee.id not in self._functions
                ) or (
                    origin is not None
                    and (
                        origin[0] == IMPORTLIB
                        or (origin[0] == BUILTINS and origin[1] == BUILTIN_IMPORT)
                    )
                )
            elif isinstance(callee, ast.Call):
                callee_reaches = (
                    isinstance(callee.func, ast.Name)
                    and callee.func.id == "getattr"
                    and bool(callee.args)
                    and isinstance(callee.args[0], ast.Name)
                    and self._package_aliases.get(callee.args[0].id) == IMPORTLIB
                )
            if isinstance(callee, ast.Name) and callee.id in rebound:
                named: str | None = f"{IMPORTLIB}.{callee.id}"
            elif callee_reaches:
                named = f"{IMPORTLIB}.{ast.unparse(callee).rsplit('.', 1)[-1]}"
            else:
                named = None
            if named is not None:
                found.append(
                    Violation(ViolationSpec(
                        self._path,
                        node.lineno,
                        "TB068",
                        f"{module_name} imports dynamically through {named}; "
                        "an import is a statement the walk can read, never a call",
                    ))
                )
        return tuple(found)

    def stray_import_violations(self) -> tuple[Violation, ...]:
        module_name = self._name
        found: list[Violation] = []
        for target, lineno in self._nested_tesser:
            found.append(
                Violation(ViolationSpec(
                    self._path,
                    lineno,
                    "TB050",
                    f"{module_name} imports {target} inside a function; "
                    "a tesser import is module-level",
                ))
            )
        for target, lineno in self._broken_relatives:
            found.append(
                Violation(ViolationSpec(
                    self._path,
                    lineno,
                    "TB043",
                    f"{module_name} imports {target} beyond the package root; "
                    "a relative import resolves inside the tree",
                ))
            )
        for edge in self._edges:
            found.extend(edge.member_form_violations())
        return tuple(found)

    def class_decls(self, registry: RegistrySpec) -> tuple[ClassDecl, ...]:
        scope = ScopeSpec(
            self._name,
            tuple(ImportSpec(local, target, original) for local, (target, original) in self._imported.items()),
            tuple(AliasSpec(alias, package) for alias, package in self._package_aliases.items()),
            tuple(self._classes),
            tuple(sorted(self._functions)),
            self._spoken,
        )
        return tuple(
            ClassDecl(ClassDeclSpec(node, self._name, self._path, scope, registry)) for node in self._class_defs
        )

    def name(self) -> str:
        return self._name

    def path(self) -> str:
        return self._path

    def debts(self) -> tuple[Debt, ...]:
        return self._debts

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

    def calls(self) -> tuple[ast.Call, ...]:
        return self._calls

    def subscripts(self) -> tuple[ast.Subscript, ...]:
        return self._subscripts

    def assignments(self) -> tuple[ast.Assign | ast.AnnAssign, ...]:
        return self._assignments

    def bound_names(self) -> tuple[tuple[str, str, str], ...]:
        return self._bound_names

    def _resolve(self, node: ast.expr) -> tuple[str, str] | None:
        if isinstance(node, ast.Subscript):
            return self._resolve(node.value)
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

    def __init__(
        self,
        sources: tuple[tuple[str, str, str | None, bool], ...],
        declared: str,
        nested: tuple[str, ...],
        symlinked: tuple[str, ...],
        exports: tuple[str, ...] = (),
        imports: tuple[str, ...] = (),
        stdlib: tuple[str, ...] = (),
        pure_stdlib: tuple[str, ...] = (),
    ) -> None:
        self.sources = sources
        self.declared = declared
        self.nested = nested
        self.symlinked = symlinked
        self.exports = exports
        self.imports = imports
        self.stdlib = stdlib
        self.pure_stdlib = pure_stdlib


class Codebase(ts.AggregateRoot):

    def __init__(self, spec: CodebaseSpec) -> None:
        modules: list[Module] = []
        broken: list[Violation] = []
        paths_by_name: dict[str, list[str]] = {}
        for path, name, _, _ in spec.sources:
            paths_by_name.setdefault(name, []).append(path)
        tops = tuple(sorted({name.split(".")[0] for _, name, _, _ in spec.sources}))
        for path, name, source, is_package in spec.sources:
            if path.endswith(STUB_SUFFIX):
                broken.append(
                    Violation(ViolationSpec(
                        path,
                        1,
                        "TB043",
                        f"{name} is a stub; a module carries its own shape, because a "
                        "stub is what the type checker reads and the walk cannot",
                    ))
                )
                continue
            others = ", ".join(other for other in paths_by_name[name] if other != path)
            if others:
                broken.append(
                    Violation(ViolationSpec(
                        path,
                        1,
                        "TB043",
                        f"{name} is also defined by {others}; a module has one definition",
                    ))
                )
                continue
            if source is None:
                broken.append(
                    Violation(ViolationSpec(
                        path,
                        1,
                        "TB043",
                        f"{name} could not be read as UTF-8 text; "
                        "every checked module is readable UTF-8 Python",
                    ))
                )
                continue
            try:
                modules.append(
                    Module(ModuleSpec(path=path, name=name, source=source, is_package=is_package, tops=tops))
                )
            except SyntaxError as error:
                broken.append(
                    Violation(ViolationSpec(
                        path,
                        error.lineno or 1,
                        "TB043",
                        f"{name} does not parse ({error.msg}); every checked module parses",
                    ))
                )
        self._modules = tuple(modules)
        self._broken = tuple(broken)
        self._declaration = spec.declared
        self._nested = spec.nested
        self._symlinked = spec.symlinked
        self._exports = spec.exports
        self._export = spec.exports[0] if len(spec.exports) == 1 else None
        self._imports = spec.imports
        self._stdlib = frozenset(spec.stdlib)
        self._pure_stdlib = spec.pure_stdlib
        self._used_imports: set[str] = set()
        self._used_pure_stdlib: set[str] = set()
        self._domain_enums: frozenset[tuple[str, str]] = frozenset()
        self._spec_makers: dict[tuple[str, str], SpecRef] = {}
        self._spec_methods: dict[str, SpecRef] = {}
        self._spec_owner: dict[Symbol, tuple[str, str]] = {}
        self._spec_takers: dict[Symbol, set[tuple[str, str]]] = {}
        self._spec_fields: dict[Symbol, dict[str, SpecRef]] = {}
        self._spec_shared: list[tuple[str, str, int, Symbol, tuple[str, str]]] = []
        self._mapper_target: dict[tuple[str, str], tuple[str, str]] = {}
        self._outcome_methods: frozenset[tuple[str, str, str]] = frozenset()

    def violations(self) -> tuple[Violation, ...]:
        declaration = self._declaration_violations()  # tesser:debt TB051
        if declaration:
            return declaration
        self._used_imports = set()
        self._used_pure_stdlib = set()
        found = list(self._broken)
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
        self._mapper_target = {}
        for module in self._modules:
            for cls in module.class_defs():
                if blocks.get((module.name(), cls.name)) != "mapper" or len(cls.bases) != 2:
                    continue
                target_key = module._resolve(cls.bases[1])
                if target_key is not None and blocks.get(target_key) in DATA_BLOCKS:
                    self._mapper_target[(module.name(), cls.name)] = target_key
        answered: dict[tuple[str, str], set[str]] = {}
        declared: dict[tuple[str, str], frozenset[str]] = {}
        inherits: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for module in self._modules:
            for cls in module.class_defs():
                declared[(module.name(), cls.name)] = frozenset(
                    item.name
                    for item in cls.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                answered[(module.name(), cls.name)] = {
                    item.name
                    for item in cls.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.returns is not None
                    and self._returns_outcome(module, item.returns, blocks)  # tesser:debt TB051
                }
                inherits[(module.name(), cls.name)] = [
                    resolved
                    for resolved in (module._resolve(base) for base in cls.bases)
                    if resolved is not None
                ]
        changed = True
        while changed:
            changed = False
            for key, base_keys in inherits.items():
                for base_key in base_keys:
                    handed = answered.get(base_key)
                    if handed is None:
                        continue
                    inherited = handed - declared[key]
                    if not inherited <= answered[key]:
                        answered[key] |= inherited
                        changed = True
        self._outcome_methods = frozenset(
            (key[0], key[1], name) for key, names in answered.items() for name in names
        )
        named: set[str] = set()
        for module in self._modules:
            parts = module.name().split(".")
            if parts[0] in ((
                        frozenset({KERNEL_PACKAGE})
                        | (frozenset({self._export}) if self._export is not None else frozenset())
                    ) & frozenset(each.name().split(".")[0] for each in self._modules)):
                continue
            if len(parts) >= 2 and parts[1] in ROLES:
                named.add(parts[0])
        contexts = frozenset(named)
        spoken: set[str] = set()
        for module in self._modules:
            if self._locate(  # tesser:debt TB051
                module.name(), module.is_package(), contexts, self._export
            ) in ("app-client", "app-client-file"):
                names_ports = module.spoken()
                if names_ports is not None:
                    spoken.add(str(names_ports))
        self._action_ports: frozenset[tuple[str, str]] = frozenset(
            key for key, block in blocks.items() if block == "port" and key[0] in spoken
        )
        self._domain_enums = frozenset(
            (module.name(), stmt.name)
            for module in self._modules
            if module.name().split(".")[1:2] == ["domain"]
            and self._locate(module.name(), module.is_package(), contexts, self._export) == "role"  # tesser:debt TB051
            for stmt in module.class_defs()
            if (module.name(), stmt.name) not in blocks
            and self._enum_base(module, stmt) is not None  # tesser:debt TB051
        )
        registry = RegistrySpec(
            KindTableSpec(tuple((module_name, class_name, block_name) for (module_name, class_name), block_name in sorted(blocks.items()))),
            tuple(SymbolSpec(module_name, class_name) for module_name, class_name in sorted(self._domain_enums)),
            tuple(f"{module_name}|{class_name}|{method_name}" for module_name, class_name, method_name in sorted(self._outcome_methods)),
            tuple(SymbolSpec(module_name, class_name) for module_name, class_name in sorted(self._action_ports)),
        )

        def constructed(policy: SignaturePolicy, decl: ClassDecl) -> tuple[Violation, ...]:
            init = decl.constructor()
            return policy.missing_constructor_violations(decl) if init is None else policy.violations(init)

        self._spec_makers = {}
        checked = [
            module
            for module in self._modules
            if self._locate(module.name(), module.is_package(), contexts, self._export)  # tesser:debt TB051
            not in TEST_TIER
        ]
        for module in checked:
            for fn in module.body():
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    made = self._spec_key(module, fn.returns, blocks)
                    if made is not None:
                        self._spec_makers[(module.name(), fn.name)] = made
        returning: dict[str, SpecRef | None] = {}
        self._spec_owner = {}
        self._spec_takers = {}
        self._spec_fields = {}
        self._spec_shared = []
        for module in checked:
            for cls in module.class_defs():
                block = blocks.get((module.name(), cls.name))
                for item in cls.body:
                    if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    params = [
                        arg
                        for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                        if arg.arg != "self"
                    ]
                    if item.name != "__init__":
                        made = self._spec_key(module, item.returns, blocks)
                        returning[item.name] = (
                            made if item.name not in returning or returning[item.name] == made else None
                        )
                    elif block in SPEC_READER_BLOCKS and len(params) == 1:
                        taken = self._spec_key(module, params[0].annotation, blocks)
                        if taken is not None and taken.shape() == SPEC_ONE:
                            first = self._spec_owner.setdefault(taken.symbol(), (module.name(), cls.name))
                            self._spec_takers.setdefault(taken.symbol(), set()).add((module.name(), cls.name))
                            if first != (module.name(), cls.name):
                                self._spec_shared.append(
                                    (module.name(), cls.name, cls.lineno, taken.symbol(), first)
                                )
                    elif block in SPEC_BLOCKS:
                        self._spec_fields[Symbol(SymbolSpec(module.name(), cls.name))] = {
                            arg.arg: field
                            for arg in params
                            if (field := self._spec_key(module, arg.annotation, blocks)) is not None
                        }
        self._spec_methods = {name: made for name, made in returning.items() if made is not None}
        self._spec_shared.sort(key=lambda entry: entry[:3])
        for module in self._modules:
            found.extend(module.comment_violations())
            found.extend(module.double_violations())
            found.extend(module.shadowing_violations())
            found.extend(module.string_equality_violations())
            found.extend(module.sibling_reference_violations())
            found.extend(module.dynamic_import_violations())
            found.extend(self._module_violations(module, blocks, contexts))  # tesser:debt TB051
            if self._locate(module.name(), module.is_package(), contexts, self._export) not in TEST_TIER:  # tesser:debt TB051
                found.extend(self._spec_use_violations(module, blocks))  # tesser:debt TB051
                found.extend(self._spec_shared_violations(module))  # tesser:debt TB051
                found.extend(module.outcome_use_violations(registry))
            if self._export == TESSER and self._locate(  # tesser:debt TB051
                module.name(), module.is_package(), contexts, self._export
            ) == "test":
                continue
            for cls, decl in zip(module.class_defs(), module.class_decls(registry)):
                block = blocks.get((module.name(), cls.name))
                if block == "aggregate":
                    found.extend(constructed(AGGREGATE_CONSTRUCTOR, decl))
                elif block == "entity":
                    found.extend(constructed(ENTITY_CONSTRUCTOR, decl))
                elif block == "component":
                    found.extend(decl.component_violations())
                elif block == "component_config":
                    found.extend(constructed(COMPONENT_CONFIG_CONSTRUCTOR, decl))
                elif block == "app_config":
                    found.extend(constructed(APP_CONFIG_CONSTRUCTOR, decl))
                elif block == "valueobject":
                    found.extend(self._valueobject_violations(module, cls, blocks))  # tesser:debt TB051
                    found.extend(decl.vo_field_violations())
                elif block == OUTCOME_BLOCK:
                    found.extend(decl.outcome_violations())
                if block in DOMAIN_BLOCKS:
                    if block == "valueobject":
                        found.extend(decl.exposure_violations())
                        found.extend(decl.composition_violations())
                        found.extend(decl.construction_path_violations())
                        found.extend(decl.exit_violations())
                    else:
                        found.extend(decl.copy_violations())
                        found.extend(decl.held_root_violations())
                        found.extend(decl.structured_exit_violations())
                    found.extend(decl.domain_method_violations())
                    found.extend(decl.outcome_field_violations())
                elif block == "spec":
                    found.extend(self._spec_violations(module, cls, blocks))  # tesser:debt TB051
                elif block in ("request", "response", "port_request", "port_response"):
                    found.extend(self._dto_violations(module, cls, blocks))  # tesser:debt TB051
                elif block == "client":
                    for signature in decl.signatures():
                        if str(signature.name()).startswith("_") and str(signature.name()) != PUBLIC_CALL:
                            continue
                        found.extend(CLIENT_METHOD.violations(signature))
                elif block in ("repository", "gateway", "handler"):
                    found.extend((HANDLER_RECORDS if block == "handler" else ADAPTER_RECORDS).violations(decl))
                    if block != "handler":
                        for body in decl.bodies():
                            found.extend(body.held_context_violations())
                elif block == "port":
                    found.extend(PORT_RECORDS.violations(decl))
                    if self._locate(  # tesser:debt TB051
                        module.name(), module.is_package(), contexts, self._export
                    ) in (
                        "ports",
                        "ports-file",
                    ):
                        found.extend(decl.port_violations())
                        for signature in decl.signatures():
                            if str(signature.name()).startswith("_") and str(signature.name()) != "__call__":
                                continue
                            found.extend(PORT_METHOD.violations(signature))
                elif block == "store":
                    if self._locate(  # tesser:debt TB051
                        module.name(), module.is_package(), contexts, self._export
                    ) in (
                        "ports",
                        "ports-file",
                    ):
                        found.extend(decl.store_violations())
                elif block == "service":
                    for body in decl.bodies():
                        found.extend(body.delegation_violations())
                        if str(body.name()) == "__init__":
                            found.extend(SERVICE_DEPENDENCIES.violations(body.signature()))
                            continue
                        if str(body.name()).startswith("_") and str(body.name()) != PUBLIC_CALL:
                            continue
                        found.extend(SERVICE_METHOD.violations(body.signature()))
                        found.extend(body.violations())
                elif block == "mapper":
                    found.extend(self._mapper_violations(module, cls, blocks))  # tesser:debt TB051
                elif block == "actions":
                    found.extend(decl.actions_violations())
                    for body in decl.bodies():
                        found.extend(body.delegation_violations())
                        if str(body.name()) == "__init__":
                            found.extend(ACTIONS_DEPENDENCIES.violations(body.signature()))
                            continue
                        if str(body.name()).startswith("_") and str(body.name()) != PUBLIC_CALL:
                            continue
                        found.extend(ACTIONS_METHOD.violations(body.signature()))
                        found.extend(body.violations())
                        found.extend(body.port_call_violations())
                elif block == "orchestrator":
                    found.extend(decl.orchestrator_violations())
                    for body in decl.bodies():
                        found.extend(body.delegation_violations())
                        if str(body.name()) == "__init__":
                            found.extend(ORCHESTRATOR_DEPENDENCIES.violations(body.signature()))
                            continue
                        if str(body.name()).startswith("_") and str(body.name()) != PUBLIC_CALL:
                            continue
                        found.extend(ORCHESTRATOR_METHOD.violations(body.signature()))
                        found.extend(body.violations())
                        found.extend(body.thread_violations())
                elif block == "actions_client" and self._locate(  # tesser:debt TB051
                    module.name(), module.is_package(), contexts, self._export
                ) in ("app-client", "app-client-file"):
                    found.extend(decl.actions_client_violations())
                    for signature in decl.signatures():
                        if str(signature.name()).startswith("_") and str(signature.name()) != "__call__":
                            continue
                        found.extend(APP_CLIENT_METHOD.violations(signature))
        found.extend(self._pairing_violations(contexts, blocks))  # tesser:debt TB051
        found.extend(self._unused_import_violations())  # tesser:debt TB051
        kept: list[Violation] = []
        used: set[tuple[str, Line]] = set()
        by_path = {module.path(): module for module in self._modules}
        for violation in found:
            owner = by_path.get(str(violation.path()))
            suppressed = False
            if owner is not None:
                for debt in owner.debts():
                    if str(debt._form) == "malformed":
                        continue
                    file_wide = str(debt._scope) == "file"
                    if file_wide and not debt._codes:
                        continue
                    if debt._codes and violation.code() not in debt._codes:
                        continue
                    if file_wide or violation.line() == debt._line:
                        used.add((owner.path(), debt._line))
                        suppressed = True
                if suppressed:
                    continue
            kept.append(violation)
        kept = list(dict.fromkeys(kept))
        for module in self._modules:
            for debt in module.debts():
                if (module.path(), debt._line) not in used:
                    kept.append(
                        Violation(ViolationSpec(
                            module.path(),
                            int(debt._line),
                            "TB090",
                            f"{module.name()} carries a debt marker that suppresses nothing; "
                            "a debt marker suppresses an actual finding",
                        ))
                    )
        return tuple(kept)

    def _pairing_violations(
        self, contexts: frozenset[str], blocks: dict[tuple[str, str], str]
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        names = {module.name() for module in self._modules if not module.is_package()}
        for module in self._modules:
            parts = module.name().split(".")
            base = parts[-1]
            place = self._locate(module.name(), module.is_package(), contexts, self._export)  # tesser:debt TB051
            parent = ".".join(parts[:-1])
            if place in PAIRED_PLACES and not module.is_package() and base != "__main__":
                saw_class = False
                declaration_only = True
                for stmt in module.body():
                    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                        continue
                    if not isinstance(stmt, ast.ClassDef) or blocks.get(
                        (module.name(), stmt.name)
                    ) not in DECLARATION_BLOCKS:
                        declaration_only = False
                        break
                    for item in stmt.body:
                        if not isinstance(item, ast.FunctionDef):
                            continue
                        if item.name == "__init__":
                            continue
                        if (
                            len(item.body) == 1
                            and isinstance(item.body[0], ast.Expr)
                            and isinstance(item.body[0].value, ast.Constant)
                        ):
                            continue
                        declaration_only = False
                        break
                    if not declaration_only:
                        break
                    saw_class = True
                if declaration_only and saw_class:
                    continue
                sibling = (parent + "." if parent else "") + "test_" + base
                if sibling not in names:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            1,
                            "TB074",
                            f"{module.name()} has no sibling test file; an implementation "
                            "module carries exactly one test_<module>.py beside it",
                        ))
                    )
            elif place == "test" and base.startswith("test_") and "tests" not in parts:
                subject = (parent + "." if parent else "") + base[len("test_") :]
                if subject not in names:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            1,
                            "TB074",
                            f"{module.name()} pairs with no implementation module; a sibling "
                            "test file is named test_<module>.py for the module beside it",
                        ))
                    )
        return tuple(found)

    @staticmethod
    def _locate(
        name: str,
        is_package: bool,
        contexts: frozenset[str],
        export: str | None = None,
    ) -> typing.Literal[
        "conftest-root",
        "conftest",
        "test",
        "eval",
        "shell-init",
        "shell-srv",
        "shell-app",
        "root-tests",
        "protocol-init",
        "protocol",
        "kernel-init",
        "kernel-file",
        "kernel",
        "root",
        "context-init",
        "context-tests-init",
        "context-tests-stray",
        "role-init",
        "role-file",
        "role",
        "ports-init",
        "ports-file",
        "ports",
        "ports-stray",
        "app-client-init",
        "app-client-file",
        "app-client",
        "app-client-stray",
        "orchestrators-init",
        "orchestrators-file",
        "orchestrators",
        "context-stray",
    ]:
        parts = name.split(".")
        basename = parts[-1]
        reserved = (
            basename == "conftest"
            or basename.startswith("test_")
            or basename.startswith(EVAL_PREFIX)
        )
        inside_application = (
            len(parts) >= 4 and parts[0] in contexts and parts[1] == PORTS_PARENT_ROLE
        )
        if inside_application and parts[2] == PORTS_PACKAGE and reserved:
            return "ports-stray"
        if inside_application and parts[2] == APPLICATION_CLIENT_PACKAGE and reserved:
            return "app-client-stray"
        if basename == "conftest":
            return "conftest-root" if len(parts) == 1 else "conftest"
        if basename.startswith("test_"):
            return "test"
        if basename.startswith(EVAL_PREFIX):
            return "eval"
        if parts[0] in APP_PACKAGES:
            if is_package:
                return "shell-init"
            if parts[0] == "srv":
                return "shell-srv"
            return "shell-app"
        if parts[0] == TESTS_ROLE:
            return "root-tests"
        if parts[0] == PROTOCOL_PACKAGE:
            return "protocol-init" if is_package else "protocol"
        if parts[0] == KERNEL_PACKAGE or (export is not None and parts[0] == export):
            if is_package:
                return "kernel-init"
            if len(parts) == 1:
                return "kernel-file"
            return "kernel"
        if parts[0] not in contexts:
            return "root"
        if len(parts) == 1:
            return "context-init"
        if parts[1] == TESTS_ROLE:
            return "context-tests-init" if is_package else "context-tests-stray"
        if parts[1] in ROLES:
            if parts[1] == PORTS_PARENT_ROLE and len(parts) >= 3 and parts[2] == PORTS_PACKAGE:
                if is_package:
                    return "ports-init"
                return "ports-file" if len(parts) == 3 else "ports"
            if (
                parts[1] == PORTS_PARENT_ROLE
                and len(parts) >= 3
                and parts[2] == APPLICATION_CLIENT_PACKAGE
            ):
                if is_package:
                    return "app-client-init"
                return "app-client-file" if len(parts) == 3 else "app-client"
            if (
                parts[1] == PORTS_PARENT_ROLE
                and len(parts) >= 3
                and parts[2] == ORCHESTRATORS_PACKAGE
            ):
                if is_package:
                    return "orchestrators-init"
                return "orchestrators-file" if len(parts) == 3 else "orchestrators"
            if is_package:
                return "role-init"
            return "role-file" if len(parts) == 2 else "role"
        return "context-stray"

    def _module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        parts = module.name().split(".")
        place = self._locate(module.name(), module.is_package(), contexts, self._export)  # tesser:debt TB051
        if place == "conftest-root":
            return self._conftest_leaf_violations(module)  # tesser:debt TB051
        if place == "conftest":
            tier_parts = module.name().split(".")
            tier_tops = (
                frozenset({KERNEL_PACKAGE})
                | (frozenset({self._export}) if self._export is not None else frozenset())
            ) & frozenset(each.name().split(".")[0] for each in self._modules)
            if tier_parts[0] in tier_tops and len(tier_parts) >= 2:
                placement: tuple[str, str] | None = ("", KERNEL_TIER)
            elif tier_parts[0] == "srv" and len(tier_parts) >= 2:
                placement = ("", SRV_TIER)
            elif tier_parts[0] == "app" and len(tier_parts) >= 2:
                placement = ("", APP_TIER)
            elif tier_parts[0] == PROTOCOL_PACKAGE and len(tier_parts) >= 2:
                placement = ("", PROTOCOL_TIER)
            elif tier_parts[0] == TESTS_ROLE and len(tier_parts) >= 2:
                placement = ("", ROOT_TESTS_TIER)
            elif len(tier_parts) < 3 or tier_parts[0] not in contexts:
                placement = None
            elif tier_parts[1] == TESTS_ROLE:
                placement = (tier_parts[0], TESTS_ROLE)
            elif tier_parts[1] not in ROLES:
                placement = (tier_parts[0], STRAY_TIER)
            elif tier_parts[1] == "adapters":
                placement = (
                    (tier_parts[0], tier_parts[2])
                    if len(tier_parts) >= 4 and tier_parts[2] in ADAPTER_TEST_TIERS
                    else (tier_parts[0], STRAY_TIER)
                )
            elif (
                tier_parts[1] == PORTS_PARENT_ROLE
                and len(tier_parts) >= 4
                and tier_parts[2] == ORCHESTRATORS_PACKAGE
            ):
                placement = (tier_parts[0], ORCHESTRATORS_PACKAGE)
            else:
                placement = (tier_parts[0], tier_parts[1])
            if placement is None or placement[1] == STRAY_TIER:
                return self._conftest_leaf_violations(module)  # tesser:debt TB051
            return tuple(
                violation
                for edge in module.import_edges()
                for violation in edge.member_form_violations()
            ) + self._test_placement_violations(module, placement[0], placement[1], contexts)  # tesser:debt TB051
        if place == "test":
            return self._test_module_violations(module, blocks, contexts)  # tesser:debt TB051
        if place == "eval":
            return self._eval_module_violations(module, blocks, contexts)  # tesser:debt TB051
        if place == "shell-init":
            return self._app_init_violations(module)  # tesser:debt TB051
        if place == "shell-srv":
            return self._srv_module_violations(module, blocks) + self._app_import_violations(  # tesser:debt TB051
                module, parts[0], contexts, blocks
            )
        if place == "shell-app":
            return self._app_module_violations(module, blocks) + self._app_import_violations(  # tesser:debt TB051
                module, parts[0], contexts, blocks
            )
        if place == "root-tests":
            return self._tests_package_violations(module, contexts)  # tesser:debt TB051
        if place == "protocol-init":
            return self._protocol_init_violations(module)  # tesser:debt TB051
        if place == "protocol":
            return self._protocol_module_violations(module, blocks, contexts)  # tesser:debt TB051
        if place == "root":
            return self._homeless_violations(module)  # tesser:debt TB051
        if place == "kernel-init":
            if self._export == TESSER and parts[0] == TESSER:
                return self._tesser_init_violations(module)  # tesser:debt TB051
            return self._kernel_init_violations(module)  # tesser:debt TB051
        if place == "kernel-file":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is a kernel module at the tree root; "
                    "kernel is a package, never a module",
                )),
            )
        if place == "kernel":
            if self._export == TESSER and parts[0] == TESSER:
                return self._tesser_shell_violations(module)  # tesser:debt TB051
            return self._kernel_module_violations(module, blocks) + self._kernel_import_violations(  # tesser:debt TB051
                module
            )
        if place == "context-init":
            return self._context_init_violations(module)  # tesser:debt TB051
        if place == "context-tests-init":
            return self._context_tests_init_violations(module)  # tesser:debt TB051
        if place == "context-tests-stray":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is neither a test module nor conftest; "
                    "a context tests package holds only test modules and conftest",
                )),
            ) + self._test_placement_violations(module, parts[0], TESTS_ROLE, contexts)  # tesser:debt TB051
        if place == "ports-stray":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is not a ports module; a ports package holds only "
                    "ports modules, and test_/eval_/conftest are reserved names, because a "
                    "fake here would be an implementation adapters may import",
                )),
            )
        if place == "ports-init":
            return self._ports_init_violations(module)  # tesser:debt TB051
        if place == "ports-file":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is a ports module; "
                    "ports is a package, never a module",
                )),
            ) + self._ports_module_violations(module, blocks)  # tesser:debt TB051
        if place == "ports":
            return self._ports_module_violations(module, blocks)  # tesser:debt TB051
        if place == "app-client-stray":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is not an application client module; an application "
                    "client package holds only client protocols, and test_/eval_/conftest "
                    "are reserved names, because a fake here would be an implementation "
                    "a job may import",
                )),
            )
        if place == "app-client-init":
            return self._package_init_violations(module, "an application client package")  # tesser:debt TB051
        if place == "app-client-file":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is an application client module; "
                    "the application client is a package, never a module",
                )),
            ) + self._application_client_module_violations(module, blocks)  # tesser:debt TB051
        if place == "app-client":
            return self._application_client_module_violations(module, blocks)  # tesser:debt TB051
        if place == "orchestrators-init":
            return self._package_init_violations(module, "an orchestrators package")  # tesser:debt TB051
        if place == "orchestrators-file":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is an orchestrators module; "
                    "orchestrators is a package, never a module",
                )),
            ) + self._orchestrators_module_violations(module, parts[0], contexts, blocks)  # tesser:debt TB051
        if place == "orchestrators":
            return self._orchestrators_module_violations(module, parts[0], contexts, blocks)  # tesser:debt TB051
        if place == "role-init":
            return self._role_init_violations(module)  # tesser:debt TB051
        if place == "role-file":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is a role module; a role is a package, never a module",
                )),
            )
        if place == "role":
            return self._role_module_violations(module, parts[1], blocks) + self._import_violations(  # tesser:debt TB051
                module, parts[0], parts[1], contexts, blocks
            )
        return (
            Violation(ViolationSpec(
                module.path(),
                1,
                "TB041",
                f"{module.name()} is not a context module; "
                "a context holds only domain, application, client, adapters, component, and tests modules",
            )),
        )

    def _context_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a context __init__ is empty",
            ))
            for stmt in module.body()
        )

    def _protocol_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a protocol __init__ is empty",
            ))
            for stmt in module.body()
        )

    def _declaration_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        if self._declaration == DECLARED_MISSING:
            found.append(
                Violation(ViolationSpec(
                    TREE_DECLARATION,
                    1,
                    "TB044",
                    "this tree is not declared; a checkable tree carries a "
                    ".tesser-root file containing 'app' at its root",
                ))
            )
        elif self._declaration == DECLARED_UNREADABLE:
            found.append(
                Violation(ViolationSpec(
                    TREE_DECLARATION,
                    1,
                    "TB044",
                    "this tree's declaration is not readable; "
                    "a .tesser-root is a plain UTF-8 text file",
                ))
            )
        elif len(self._exports) > 1:
            found.append(
                Violation(ViolationSpec(
                    TREE_DECLARATION,
                    1,
                    "TB044",
                    "this tree declares a second exported kernel; a tree has one "
                    "exported kernel, so a declaration carries at most one "
                    "'export <dir>' line",
                ))
            )
        elif self._declaration != DECLARED_APP:
            found.append(
                Violation(ViolationSpec(
                    TREE_DECLARATION,
                    1,
                    "TB044",
                    "this tree declares an unrecognized kind; a declaration is "
                    "'app', then only 'skip <dir>', 'export <dir>', "
                    "'import <package>', and 'stdlib <module>' lines",
                ))
            )
        if len(self._exports) <= 1:
            found.extend(self._export_declaration_violations())  # tesser:debt TB051
            found.extend(self._import_declaration_violations())  # tesser:debt TB051
            found.extend(self._stdlib_declaration_violations())  # tesser:debt TB051
        for relative in self._nested:
            found.append(
                Violation(ViolationSpec(
                    relative,
                    1,
                    "TB044",
                    "declares a nested tree root; a tessercheck run covers one "
                    "declared tree, so run that tree directly",
                ))
            )
        for relative in self._symlinked:
            found.append(
                Violation(ViolationSpec(
                    relative,
                    1,
                    "TB045",
                    "is a symlinked directory; a declared tree is walked in "
                    "full, and a symlink escapes the walk",
                ))
            )
        return tuple(found)

    def _export_declaration_violations(self) -> tuple[Violation, ...]:
        if self._export is None:
            return ()
        if self._export == KERNEL_PACKAGE or self._export in SHELL_PACKAGES:
            return (
                Violation(ViolationSpec(
                    TREE_DECLARATION,
                    1,
                    "TB044",
                    f"this tree exports '{self._export}'; an exported kernel "
                    "never takes the name of the kernel package or the app shell",
                )),
            )
        if not any(
            module.name() == self._export and module.is_package()
            for module in self._modules
        ):
            return (
                Violation(ViolationSpec(
                    TREE_DECLARATION,
                    1,
                    "TB044",
                    f"this tree exports '{self._export}' but no such package "
                    "exists; an export names a package at the tree root",
                )),
            )
        if self._export == TESSER:
            outsiders = sorted(
                frozenset(
                    module.name().split(".")[0] for module in self._modules
                )
                - frozenset({TESSER, TESTS_ROLE, "conftest"})
            )
            if outsiders:
                return (
                    Violation(ViolationSpec(
                        TREE_DECLARATION,
                        1,
                        "TB044",
                        f"this tree exports 'tesser' but also holds {', '.join(outsiders)}; "
                        "a tree exporting tesser is the distribution itself — "
                        "its top level is tesser and tests, nothing else",
                    )),
                )
        if self._export != TESSER and any(
            len(parts) >= 2 and parts[0] == self._export and parts[1] in ROLES
            for parts in (module.name().split(".") for module in self._modules)
        ):
            return (
                Violation(ViolationSpec(
                    TREE_DECLARATION,
                    1,
                    "TB044",
                    f"this tree exports '{self._export}', a context-shaped package; "
                    "a bounded context's domain is never exported — a kernel is not a context",
                )),
            )
        return ()

    def _import_declaration_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        tops = (frozenset(each.name().split(".")[0] for each in self._modules))
        for declared in self._imports:
            head = declared.split(".")[0]
            if head == KERNEL_PACKAGE or head in SHELL_PACKAGES or head in tops:
                found.append(
                    Violation(ViolationSpec(
                        TREE_DECLARATION,
                        1,
                        "TB044",
                        f"this tree declares 'import {declared}' but that names "
                        "this tree; an import declaration names an installed "
                        "external kernel, never something the walk governs",
                    ))
                )
            elif head in self._stdlib:
                found.append(
                    Violation(ViolationSpec(
                        TREE_DECLARATION,
                        1,
                        "TB044",
                        f"this tree declares 'import {declared}' but that names "
                        "the stdlib; the pure stdlib is already legal and the "
                        "rest of it is never a kernel",
                    ))
                )
        return tuple(found)

    def _unused_import_violations(self) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                TREE_DECLARATION,
                1,
                "TB044",
                f"this tree declares 'import {declared}' and nothing uses it; "
                "an import declaration that legalizes nothing is itself a finding",
            ))
            for declared in self._imports
            if declared not in self._used_imports
        ) + tuple(
            Violation(ViolationSpec(
                TREE_DECLARATION,
                1,
                "TB044",
                f"this tree declares 'stdlib {declared}' and nothing uses it; "
                "a stdlib declaration that legalizes nothing is itself a finding",
            ))
            for declared in self._pure_stdlib
            if declared not in self._used_pure_stdlib
        )

    def _stdlib_declaration_violations(self) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for declared in self._pure_stdlib:
            head = declared.split(".")[0]
            if head not in self._stdlib:
                found.append(
                    Violation(ViolationSpec(
                        TREE_DECLARATION,
                        1,
                        "TB044",
                        f"this tree declares 'stdlib {declared}' but that is not "
                        "the stdlib; a stdlib declaration widens the domain's pure "
                        "stdlib, an external package is declared with import",
                    ))
                )
            elif declared in CORE_STDLIB["domain"] or head in CORE_STDLIB["domain"]:
                found.append(
                    Violation(ViolationSpec(
                        TREE_DECLARATION,
                        1,
                        "TB044",
                        f"this tree declares 'stdlib {declared}' but the domain "
                        "already imports it; a stdlib declaration widens the default "
                        "pure stdlib, never repeats it",
                    ))
                )
        return tuple(found)

    def _pure_domain_import(self, target: str) -> bool:
        head = target.split(".")[0]
        if target in CORE_STDLIB["domain"] or head in CORE_STDLIB["domain"]:
            return True
        for declared in self._pure_stdlib:
            if target == declared or target.startswith(declared + "."):
                self._used_pure_stdlib.add(declared)
                return True
        return False

    def _homeless_violations(self, module: Module) -> tuple[Violation, ...]:
        return (
            Violation(ViolationSpec(
                module.path(),
                1,
                "TB040",
                f"{module.name()} belongs to no governed package; "
                "every module belongs to a context, a kernel, srv, app, tests, "
                "or the protocol package",
            )),
        )

    def _conftest_leaf_violations(self, module: Module) -> tuple[Violation, ...]:
        tops = (frozenset(each.name().split(".")[0] for each in self._modules))
        if self._export != TESSER:
            tops = tops - {TESSER}
        return tuple(
            violation
            for edge in module.import_edges()
            for violation in edge.member_form_violations()
        ) + tuple(
            Violation(ViolationSpec(
                module.path(),
                lineno,
                "TB065",
                f"{module.name()} imports {target}; "
                "a conftest is a leaf that imports nothing from its tree",
            ))
            for target, lineno in (
                (str(edge._target), int(edge._lineno))
                for edge in module.import_edges()
                if str(edge._target).split(".")[0] in tops
            )
        )

    def _tests_package_violations(
        self,
        module: Module,
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        if len(module.name().split(".")) == 1:
            return tuple(
                Violation(ViolationSpec(
                    module.path(),
                    stmt.lineno,
                    "TB041",
                    f"{module.name()} __init__ declares code; "
                    "a tests package holds only test modules and conftest",
                ))
                for stmt in module.body()
            )
        return (
            Violation(ViolationSpec(
                module.path(),
                1,
                "TB041",
                f"{module.name()} is neither a test module nor conftest; "
                "a tests package holds only test modules and conftest",
            )),
        ) + self._test_placement_violations(module, "", ROOT_TESTS_TIER, contexts)  # tesser:debt TB051

    def _context_tests_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a context tests __init__ is empty",
            ))
            for stmt in module.body()
        )

    def _role_init_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB042",
                        f"{module.name()} __init__ declares code; "
                        "a role __init__ only re-exports from its own role",
                    ))
                )
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            if not target.startswith(module.name() + "."):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB042",
                        f"{module.name()} imports {target}; "
                        "a role __init__ only re-exports from its own role",
                    ))
                )
            found.extend(edge.member_form_violations())
            found.extend(self._form_violations(module, edge))  # tesser:debt TB051
        return tuple(found)

    def _tesser_init_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        parts = module.name().split(".")
        if (
            len(parts) >= 2
            and not parts[1].startswith(DO_NOT_USE_PREFIX)
            and parts[1] not in TESSER_NAMESPACES
        ):
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is not a consumer namespace; the tesser "
                    "distribution holds only the namespaces its consumers import",
                ))
            )
        for stmt in module.body():
            if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB042",
                        f"{module.name()} __init__ declares code; "
                        "a tesser __init__ only re-exports from the distribution",
                    ))
                )
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            if not target.startswith(TESSER + "."):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB042",
                        f"{module.name()} imports {target}; "
                        "a tesser __init__ only re-exports from the distribution",
                    ))
                )
        return tuple(found)

    def _tesser_shell_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(module.stray_import_violations())
        parts = module.name().split(".")
        if not parts[1].startswith(DO_NOT_USE_PREFIX) and parts[1] not in TESSER_NAMESPACES:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is not a consumer namespace; the tesser "
                    "distribution holds only the namespaces its consumers import",
                ))
            )
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            head = target.split(".")[0]
            if head == TESSER or head in TESSER_STDLIB:
                continue
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    lineno,
                    "TB062",
                    f"{module.name()} imports {target}; a shell module imports "
                    "only the tesser distribution and the shell stdlib",
                ))
            )
        return tuple(found)

    def _kernel_init_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB042",
                        f"{module.name()} __init__ declares code; "
                        "a kernel __init__ only re-exports from its own kernel",
                    ))
                )
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            if not target.startswith(module.name() + "."):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB042",
                        f"{module.name()} imports {target}; "
                        "a kernel __init__ only re-exports from its own kernel",
                    ))
                )
        return tuple(found)

    def _kernel_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}"
                if block is None:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} declares no ts.* base; every kernel class declares its block",
                        ))
                    )
                elif KIND_ROLE.get(block) != "domain":
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}; a kernel holds only domain kinds — "
                            "value objects, entities, aggregates, and specs",
                        ))
                    )
        found.extend(
            self._module_function_violations(module, "kernel")  # tesser:debt TB051
        )
        found.extend(
            self._statement_violations(  # tesser:debt TB051
                module,
                "kernel",
                "a kernel module holds only imports, classes, and Final constants",
                None,
            )
        )
        return tuple(found)

    def _kernel_import_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(module.stray_import_violations())
        found.extend(
            self._tesser_import_violations(  # tesser:debt TB051
                module,
                "kernel",
                ROLE_TESSER_PACKAGE["domain"],
                "a kernel module imports only tesser.domain",
                "a kernel module imports tesser.domain exactly once, as ts",
                "a kernel module imports tesser.domain exactly once, as ts",
                norms=NORM_IMPORTS["domain"],
            )
        )
        own = (
            frozenset({self._export})
            if module.name().split(".")[0] == self._export
            else ((
                        frozenset({KERNEL_PACKAGE})
                        | (frozenset({self._export}) if self._export is not None else frozenset())
                    ) & frozenset(each.name().split(".")[0] for each in self._modules))
        )
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            pieces = target.split(".")
            if pieces[0] == TESSER:
                continue
            if pieces[0] in own and (any(
                        module.name() == target or module.name().startswith(target + ".")
                        for module in self._modules
                    )):
                continue
            covered = False
            for declared in self._imports:
                if target == declared or target.startswith(declared + "."):
                    self._used_imports.add(declared)
                    covered = True
                    break
            if covered:
                continue
            if self._pure_domain_import(target):  # tesser:debt TB051
                continue
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    lineno,
                    "TB062",
                    f"{module.name()} imports {target}; a kernel imports only its "
                    "kernel, tesser.domain, declared kernels, and the pure stdlib",
                ))
            )
        return tuple(found)

    def _app_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a srv or app __init__ is empty",
            ))
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
        norms: frozenset[str] = frozenset(),
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        seen_own = False
        seen_any = False
        for imp in module.tesser_imports():
            target = str(imp._target)
            lineno = int(imp._lineno)
            if target in norms:
                if str(imp._form) == "bare":
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB050",
                            f"{module.name()} imports {target} without an alias; a norm "
                            "module is imported as an aliased module — a bare import binds "
                            "the whole tesser package, and the ts alias belongs to the "
                            "placement's own package",
                        ))
                    )
                continue
            seen_any = True
            if target != package:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB050",
                        f"{module.name()} imports {target}; {only_clause}",
                    ))
                )
            elif seen_own:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB050",
                        f"{module.name()} imports {target} again; {once_clause}",
                    ))
                )
            else:
                seen_own = True
                if str(imp._form) == "from":
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB050",
                            f"{module.name()} imports names from {target}; {once_clause}",
                        ))
                    )
                elif str(imp._form) in ("alias", "bare"):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB050",
                            f"{module.name()} imports {target} without the ts alias; {once_clause}",
                        ))
                    )
        if absent_clause is not None and not seen_any:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB050",
                    f"{module.name()} never imports {package}; {absent_clause}",
                ))
            )
        return tuple(found)

    def _module_function_violations(self, module: Module, subject: str) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()}.{stmt.name} is a module function; "
                        f"a {subject} module holds classes, never functions",
                    ))
                )
        return tuple(found)

    def _statement_violations(
        self,
        module: Module,
        subject: str,
        loose_clause: str,
        entry: str | None,
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for stmt in module.body():
            if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.ClassDef)):
                continue
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if (
                entry is not None
                and isinstance(stmt, ast.If)
                and isinstance(stmt.test, ast.Compare)
                and isinstance(stmt.test.left, ast.Name)
                and stmt.test.left.id == "__name__"
                and len(stmt.test.ops) == 1
                and isinstance(stmt.test.ops[0], ast.Eq)
                and len(stmt.test.comparators) == 1
                and isinstance(stmt.test.comparators[0], ast.Constant)
                and stmt.test.comparators[0].value == "__main__"
            ):
                if not (
                    not stmt.orelse
                    and len(stmt.body) == 1
                    and isinstance(stmt.body[0], ast.Expr)
                    and isinstance(stmt.body[0].value, ast.Call)
                    and module._resolve(stmt.body[0].value.func) == TESSER_ENTRY
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB051",
                            f"{module.name()} has a __main__ guard holding more than "
                            f"{entry}(run); a srv module's entry point is {entry}(run) "
                            "and nothing else",
                        ))
                    )
                continue
            if isinstance(stmt, ast.AnnAssign):
                annotation = ast.unparse(stmt.annotation)
                if not (
                    annotation in ("Final", "typing.Final")
                    or annotation.startswith(("Final[", "typing.Final["))
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB051",
                            f"{module.name()} declares a module constant without Final; "
                            f"{subject} constants are Final",
                        ))
                    )
            elif isinstance(stmt, ast.Assign):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()} declares a module constant without Final; "
                        f"{subject} constants are Final",
                    ))
                )
            else:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()} has a loose module-level statement; {loose_clause}",
                    ))
                )
        return tuple(found)

    @staticmethod
    def _unquoted(node: ast.expr | None) -> ast.expr | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                return ast.parse(node.value, mode="eval").body
            except SyntaxError:
                return None
        return node

    def _spec_shared_violations(self, module: Module) -> tuple[Violation, ...]:
        found: list[Violation] = []
        for shared_module, shared_class, line, shared_spec, shared_owner in self._spec_shared:
            if shared_module != module.name():
                continue
            spec_label = f"{shared_spec.module()}.{shared_spec.name()}"
            owner_label = ".".join(shared_owner)
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    line,
                    "TB083",
                    f"{module.name()}.{shared_class} takes {spec_label}, which {owner_label} already takes; "
                    "a spec constructs exactly one object",
                ))
            )
        return tuple(found)

    def _spec_key(
        self, module: Module, node: ast.expr | None, blocks: dict[tuple[str, str], str]
    ) -> SpecRef | None:
        if node is None:
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                node = ast.parse(node.value, mode="eval").body
            except SyntaxError:
                return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self._spec_key(module, node.left, blocks) or self._spec_key(module, node.right, blocks)
        if isinstance(node, ast.Subscript):
            head = Codebase._annotation_head(node)
            inner = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            if head in ("Optional", "Union"):
                for each in inner:
                    found = self._spec_key(module, each, blocks)
                    if found is not None:
                        return found
                return None
            if head in ("tuple", "list", "set", "frozenset", "Sequence", "Iterable", "Collection"):
                for each in inner:
                    found = self._spec_key(module, each, blocks)
                    if found is not None and found.shape() == SPEC_ONE:
                        return found.many()
            return None
        key = module._resolve(node)
        if key is not None and blocks.get(key) == "mapper":
            key = self._mapper_target.get(key)
        if key is not None and blocks.get(key) in SPEC_BLOCKS:
            return SpecRef(SpecRefSpec(SymbolSpec(key[0], key[1]), "one"))
        return None

    def _spec_use_violations(
        self, module: Module, blocks: dict[tuple[str, str], str]
    ) -> tuple[Violation, ...]:
        def annotation(node: ast.expr | None) -> SpecRef | None:
            return self._spec_key(module, node, blocks)

        def maker(node: ast.expr) -> SpecRef | None:
            made = annotation(node)
            if made is not None:
                return made
            if isinstance(node, ast.Name):
                return self._spec_makers.get((module.name(), node.id))
            key = module._resolve(node)
            if key is not None and key in self._spec_makers:
                return self._spec_makers[key]
            if isinstance(node, ast.Attribute):
                return self._spec_methods.get(node.attr)
            return None

        def typed(node: ast.expr, names: dict[str, SpecRef]) -> SpecRef | None:
            if isinstance(node, (ast.Await, ast.NamedExpr)):
                return typed(node.value, names)
            if isinstance(node, ast.Name):
                return names.get(node.id)
            if isinstance(node, ast.Call):
                made = maker(node.func)
                if made is not None:
                    return made
                if isinstance(node.func, ast.Name) and node.func.id == "enumerate" and node.args:
                    return typed(node.args[0], names)
                return None
            if isinstance(node, ast.Attribute):
                owner = typed(node.value, names)
                if owner is not None and owner.shape() == SPEC_ONE:
                    return self._spec_fields.get(owner.symbol(), {}).get(node.attr)
                return None
            if isinstance(node, ast.Subscript):
                owner = typed(node.value, names)
                if owner is not None and owner.shape() == SPEC_MANY:
                    return owner if isinstance(node.slice, ast.Slice) else owner.one()
                return None
            if isinstance(node, ast.IfExp):
                return typed(node.body, names) or typed(node.orelse, names)
            if isinstance(node, ast.BoolOp):
                for each in node.values:
                    found = typed(each, names)
                    if found is not None:
                        return found
            return None

        def carried(node: ast.expr, names: dict[str, SpecRef]) -> str | None:
            if isinstance(node, (ast.Name, ast.Call, ast.Attribute, ast.Subscript)) and typed(node, names) is not None:
                if isinstance(node, ast.Name):
                    return node.id
                if isinstance(node, ast.Call) and maker(node.func) is not None:
                    return ast.unparse(node.func)
                return ast.unparse(node)
            parts: list[ast.expr] = []
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                parts = list(node.elts)
            elif isinstance(node, ast.Dict):
                parts = [value for value in node.values if value is not None]
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in ("list", "tuple", "set", "frozenset", "dict")
            ):
                parts = [*node.args, *(k.value for k in node.keywords)]
            elif isinstance(node, ast.IfExp):
                parts = [node.body, node.orelse]
            elif isinstance(node, ast.BoolOp):
                parts = list(node.values)
            elif isinstance(node, (ast.Await, ast.NamedExpr)):
                parts = [node.value]
            for each in parts:
                hit = carried(each, names)
                if hit is not None:
                    return hit
            return None

        def bound(fn: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda) -> set[str]:
            args = fn.args
            out = {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
            if args.vararg is not None:
                out.add(args.vararg.arg)
            if args.kwarg is not None:
                out.add(args.kwarg.arg)
            return out

        def scope(nodes: list[ast.AST]) -> list[ast.AST]:
            out: list[ast.AST] = []
            stack = list(nodes)
            while stack:
                cur = stack.pop()
                out.append(cur)
                if isinstance(
                    cur,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                        ast.Lambda,
                        ast.ClassDef,
                        ast.ListComp,
                        ast.SetComp,
                        ast.DictComp,
                        ast.GeneratorExp,
                    ),
                ):
                    continue
                stack.extend(ast.iter_child_nodes(cur))
            return out

        def stored(node: ast.AST) -> list[str]:
            return [t.id for t in ast.walk(node) if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)]

        def element(target: ast.expr, iterable: ast.expr, names: dict[str, SpecRef]) -> tuple[str, SpecRef] | None:
            many = typed(iterable, names)
            if many is None or many.shape() != SPEC_MANY:
                return None
            if isinstance(target, ast.Name):
                return target.id, many.one()
            if (
                isinstance(target, ast.Tuple)
                and len(target.elts) == 2
                and isinstance(target.elts[1], ast.Name)
                and isinstance(iterable, ast.Call)
                and isinstance(iterable.func, ast.Name)
                and iterable.func.id == "enumerate"
            ):
                return target.elts[1].id, many.one()
            return None

        def held_in(body: list[ast.stmt], names: dict[str, SpecRef]) -> dict[str, SpecRef]:
            names = dict(names)
            local = scope(list(body))
            local.extend(
                inner
                for node in local
                if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
                for inner in ast.walk(node)
                if isinstance(inner, ast.NamedExpr)
            )
            changed = True
            while changed:
                changed = False
                for node in local:
                    if isinstance(node, ast.Assign):
                        made = typed(node.value, names)
                        if made is not None:
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id not in names:
                                    names[target.id] = made
                                    changed = True
                    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                        made = annotation(node.annotation) or (
                            typed(node.value, names) if node.value is not None else None
                        )
                        if made is not None and node.target.id not in names:
                            names[node.target.id] = made
                            changed = True
                    elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
                        made = typed(node.value, names)
                        if made is not None and node.target.id not in names:
                            names[node.target.id] = made
                            changed = True
                    elif isinstance(node, (ast.For, ast.AsyncFor)):
                        picked = element(node.target, node.iter, names)
                        if picked is not None and picked[0] not in names:
                            names[picked[0]] = picked[1]
                            changed = True
            shadowed: set[str] = set()
            for node in local:
                if isinstance(node, (ast.For, ast.AsyncFor)):
                    if element(node.target, node.iter, names) is None:
                        shadowed.update(stored(node.target))
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    for item in node.items:
                        if item.optional_vars is not None:
                            shadowed.update(stored(item.optional_vars))
                elif isinstance(node, ast.ExceptHandler) and node.name is not None:
                    shadowed.add(node.name)
                elif isinstance(node, ast.Assign) and typed(node.value, names) is None:
                    for target in node.targets:
                        shadowed.update(stored(target))
                elif isinstance(node, ast.AnnAssign) and annotation(node.annotation) is None and (
                    node.value is None or typed(node.value, names) is None
                ):
                    shadowed.update(stored(node.target))
                elif isinstance(node, ast.AugAssign):
                    shadowed.update(stored(node.target))
                elif isinstance(node, ast.NamedExpr) and typed(node.value, names) is None:
                    shadowed.update(stored(node.target))
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    shadowed.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.Match):
                    for case in node.cases:
                        for pattern in ast.walk(case.pattern):
                            if isinstance(pattern, (ast.MatchAs, ast.MatchStar)) and pattern.name is not None:
                                shadowed.add(pattern.name)
                            elif isinstance(pattern, ast.MatchMapping) and pattern.rest is not None:
                                shadowed.add(pattern.rest)
            return {name: made for name, made in names.items() if name not in shadowed}

        def held(fn: ast.FunctionDef | ast.AsyncFunctionDef, names: dict[str, SpecRef]) -> dict[str, SpecRef]:
            seeded = dict(names)
            for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
                made = annotation(a.annotation)
                if made is not None:
                    seeded[a.arg] = made
            return held_in(list(fn.body), seeded)

        def kept(node: ast.AST, names: dict[str, SpecRef], top: bool) -> str | None:
            if top and isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) for t in node.targets):
                return carried(node.value, names)
            if top and isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.value is not None:
                    return carried(node.value, names)
                return ast.unparse(node.annotation) if annotation(node.annotation) is not None else None
            if isinstance(node, ast.Assign) and any(
                isinstance(t, (ast.Attribute, ast.Subscript))
                for target in node.targets
                for t in (target.elts if isinstance(target, (ast.Tuple, ast.List)) else [target])
            ):
                return carried(node.value, names)
            if isinstance(node, ast.AugAssign) and isinstance(node.target, (ast.Attribute, ast.Subscript)):
                return carried(node.value, names)
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, (ast.Attribute, ast.Subscript)):
                if node.value is not None:
                    return carried(node.value, names)
                return ast.unparse(node.annotation) if annotation(node.annotation) is not None else None
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr in (
                    "append", "appendleft", "extend", "insert", "setdefault"
                ):
                    for each in [*node.args, *(k.value for k in node.keywords)]:
                        hit = carried(each, names)
                        if hit is not None:
                            return hit
                if isinstance(node.func, ast.Attribute) and node.func.attr == "__setattr__":
                    if len(node.args) == 3:
                        return carried(node.args[2], names)
                    if len(node.args) == 2:
                        return carried(node.args[1], names)
                if isinstance(node.func, ast.Name) and node.func.id == "setattr" and len(node.args) == 3:
                    return carried(node.args[2], names)
            return None

        def read(node: ast.AST, names: dict[str, SpecRef]) -> tuple[str, str, Symbol] | None:
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                owner = typed(node.value, names)
                if owner is not None and owner.shape() == SPEC_ONE and not node.attr.startswith("__"):
                    return ast.unparse(node.value), node.attr, owner.symbol()
                return None
            if isinstance(node, ast.Call) and node.args:
                owner = typed(node.args[0], names)
                if owner is None or owner.shape() == SPEC_MANY:
                    return None
                if isinstance(node.func, ast.Name) and node.func.id in ("getattr", "vars"):
                    field = (
                        node.args[1].value
                        if len(node.args) > 1
                        and isinstance(node.args[1], ast.Constant)
                        and isinstance(node.args[1].value, str)
                        else "__dict__"
                    )
                    return ast.unparse(node.args[0]), field, owner.symbol()
                if ast.unparse(node.func).split(".")[-1] in ("asdict", "astuple", "copy", "deepcopy"):
                    return ast.unparse(node.args[0]), "__dict__", owner.symbol()
            return None

        found: list[Violation] = []
        seen: set[tuple[int, str, str]] = set()

        def scan(
            nodes: list[ast.AST],
            names: dict[str, SpecRef],
            where: str,
            owner_here: tuple[str, str] | None,
            assembling: bool,
            top: bool = False,
        ) -> None:
            for cur in scope(nodes):
                if top and isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if top and isinstance(cur, ast.ClassDef):
                    scan(list(cur.body), names, f"{where}.{cur.name}", None, False, True)
                    continue
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    scan(
                        list(cur.body),
                        held(cur, {n: t for n, t in names.items() if n not in bound(cur)}),
                        f"{where}.{cur.name}",
                        owner_here,
                        assembling,
                    )
                    continue
                if isinstance(cur, ast.Lambda):
                    scan(
                        [cur.body],
                        {n: t for n, t in names.items() if n not in bound(cur)},
                        where,
                        owner_here,
                        assembling,
                    )
                    continue
                if isinstance(cur, ast.ClassDef):
                    scan(list(cur.body), names, f"{where}.{cur.name}", owner_here, assembling)
                    continue
                if isinstance(cur, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    first, rest = cur.generators[0], cur.generators[1:]
                    scan([first.iter], names, where, owner_here, assembling)
                    targets = {
                        t.id
                        for comp in cur.generators
                        for t in ast.walk(comp.target)
                        if isinstance(t, ast.Name)
                    }
                    inner = {n: t for n, t in names.items() if n not in targets}
                    for comp in cur.generators:
                        picked = element(comp.target, comp.iter, inner if comp is not first else names)
                        if picked is not None:
                            inner[picked[0]] = picked[1]
                    parts: list[ast.AST] = [*first.ifs]
                    for comp in rest:
                        parts.extend([comp.iter, *comp.ifs])
                    parts.extend([cur.key, cur.value] if isinstance(cur, ast.DictComp) else [cur.elt])
                    scan(parts, inner, where, owner_here, assembling)
                    continue
                if not isinstance(cur, (ast.stmt, ast.expr)):
                    continue
                spec_name = kept(cur, names, top)
                if spec_name is not None and not assembling and (cur.lineno, "\x00keeps", spec_name) not in seen:
                    seen.add((cur.lineno, "\x00keeps", spec_name))
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            cur.lineno,
                            "TB083",
                            f"{where} keeps the spec {spec_name!r}; "
                            "a spec is never kept, it initializes its own object and is done",
                        ))
                    )
                hit = read(cur, names)
                if hit is not None:
                    spec_name, field, key = hit
                    licensed = owner_here is not None and owner_here in self._spec_takers.get(key, set())
                    if not licensed and (cur.lineno, field, spec_name) not in seen:
                        seen.add((cur.lineno, field, spec_name))
                        found.append(
                            Violation(ViolationSpec(
                                module.path(),
                                cur.lineno,
                                "TB083",
                                f"{where} reads {field!r} of the spec {spec_name!r}; "
                                "a spec is only read where it initializes its own object",
                            ))
                        )

        def roots() -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.ClassDef | None]]:
            out: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.ClassDef | None]] = []
            stack: list[tuple[ast.AST, ast.ClassDef | None]] = [(stmt, None) for stmt in module.body()]
            while stack:
                cur, cls = stack.pop()
                if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append((cur, cls))
                    continue
                if isinstance(cur, ast.Lambda):
                    continue
                if isinstance(cur, ast.ClassDef):
                    stack.extend((item, cur) for item in cur.body)
                    continue
                stack.extend((child, cls) for child in ast.iter_child_nodes(cur))
            return out

        module_names = held_in(list(module.body()), {})
        scan(list(module.body()), module_names, module.name(), None, False, True)
        for fn, cls in roots():
            block = blocks.get((module.name(), cls.name)) if cls is not None else None
            where = (
                f"{module.name()}.{cls.name}.{fn.name}" if cls is not None else f"{module.name()}.{fn.name}"
            )
            scan(
                list(fn.body),
                held(fn, module_names),
                where,
                (module.name(), cls.name)
                if cls is not None and fn.name == "__init__" and block in SPEC_READER_BLOCKS
                else None,
                fn.name == "__init__" and block in SPEC_BLOCKS,
            )
        return tuple(sorted(found, key=lambda v: int(v.line())))

    @staticmethod
    def _names_bool(node: ast.expr | None) -> bool:
        if node is None:
            return False
        head = node
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            try:
                head = ast.parse(head.value, mode="eval").body
            except SyntaxError:
                return False
        if isinstance(head, ast.BinOp) and isinstance(head.op, ast.BitOr):
            return Codebase._names_bool(head.left) or Codebase._names_bool(head.right)
        if isinstance(head, ast.Subscript) and Codebase._annotation_head(head) in (
            "Optional",
            "Final",
            "Annotated",
        ):
            wrapped = head.slice
            if isinstance(wrapped, ast.Tuple) and wrapped.elts:
                wrapped = wrapped.elts[0]
            return Codebase._names_bool(wrapped)
        return isinstance(head, ast.Name) and head.id == "bool"

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

    def _app_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(module.stray_import_violations())
        found.extend(
            self._tesser_import_violations(  # tesser:debt TB051
                module,
                "app",
                "tesser.app",
                "an app module's tesser imports are tesser.app, "
                "and tesser.errors",
                "an app module imports tesser.app exactly once, as ts",
                "an app module imports tesser.app exactly once, as ts",
                NORM_IMPORTS["app"],
            )
        )
        for stmt in module.body():
            if isinstance(stmt, ast.FunctionDef) and not (any(
                        key is not None and TESSER_DECORATORS.get(key) == ("load")
                        for key in (module._resolve(decorator) for decorator in stmt.decorator_list)
                    )):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()}.{stmt.name} is an undeclared module function; "
                        "an app function declares itself with @ts.load",
                    ))
                )
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}"
                if block is None:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} declares no ts.* base; "
                            "every app class declares its block",
                        ))
                    )
                elif block not in APP_KINDS:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}; only an app, an app loader, an app "
                            "config, an app config spec, and a config repository live in an "
                            "app module",
                        ))
                    )
        found.extend(
            self._statement_violations(  # tesser:debt TB051
                module,
                "app",
                "an app module holds only imports, classes, declared functions, and Final constants",
                None,
            )
        )
        return tuple(found)

    def _srv_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(module.stray_import_violations())
        found.extend(
            self._tesser_import_violations(  # tesser:debt TB051
                module,
                "srv",
                "tesser.srv",
                "a srv module's tesser imports are tesser.srv, "
                "and tesser.errors",
                "a srv module imports tesser.srv exactly once, as ts",
                "a srv module imports tesser.srv exactly once, as ts",
                NORM_IMPORTS["srv"],
            )
        )
        for stmt in module.body():
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}"
                if block is None:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} declares no ts.* base; a srv class declares its block",
                        ))
                    )
                elif block != "host":
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}; only a host class lives in a srv module",
                        ))
                    )
        found.extend(
            self._module_function_violations(module, "srv")  # tesser:debt TB051
        )
        found.extend(
            self._statement_violations(  # tesser:debt TB051
                module,
                "srv",
                "a srv module holds only imports, declared classes, and Final constants",
                "ts.main",
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
        found.extend(module.stray_import_violations())
        found.extend(
            self._tesser_import_violations(  # tesser:debt TB051
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
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB064",
                        f"{module.name()} imports {target}; "
                        "a protocol module is context-generic and imports no context",
                    ))
                )
            elif head in APP_PACKAGES:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB064",
                        f"{module.name()} imports {target}; "
                        "a protocol module never imports srv or app",
                    ))
                )
            elif head != PROTOCOL_PACKAGE and head in (frozenset(each.name().split(".")[0] for each in self._modules)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB064",
                        f"{module.name()} imports {target}; "
                        "a protocol module imports nothing else from its tree",
                    ))
                )
        for stmt in module.body():
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}"
                if block is None:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} declares no ts.* base; a protocol class declares its block",
                        ))
                    )
                elif block not in PROTOCOL_KINDS:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}; only protocol ports, protocol records, "
                            "protocol rejections, protocol requests, and protocol responses live in a protocol module",
                        ))
                    )
        found.extend(
            self._module_function_violations(module, "protocol")  # tesser:debt TB051
        )
        found.extend(
            self._statement_violations(  # tesser:debt TB051
                module,
                "protocol",
                "a protocol module holds only imports, declared classes, and Final constants",
                None,
            )
        )
        return tuple(found)

    @classmethod
    def _own_scope_returns(cls, node: ast.AST) -> list[ast.Return]:
        found: list[ast.Return] = []
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
            ):
                continue
            if isinstance(child, ast.Return):
                found.append(child)
            found.extend(cls._own_scope_returns(child))
        return found

    @classmethod
    def _nested_class_defs(cls, body: list[ast.stmt]) -> list[ast.ClassDef]:
        found: list[ast.ClassDef] = []
        for stmt in body:
            if isinstance(stmt, ast.ClassDef):
                found.append(stmt)
                found.extend(cls._nested_class_defs(stmt.body))
        return found

    @classmethod
    def _is_union(cls, node: ast.expr | None) -> bool:
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return True
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id in ("Optional", "Union"):
                return True
            elements = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            return any(cls._is_union(element) for element in elements)
        if isinstance(node, ast.Attribute):
            return node.attr in ("Optional", "Union")
        return False

    def _ports_init_violations(self, module: Module) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; a ports __init__ is empty",
            ))
            for stmt in module.body()
        )

    def _package_init_violations(self, module: Module, subject: str) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                module.path(),
                stmt.lineno,
                "TB042",
                f"{module.name()} __init__ declares code; {subject} __init__ is empty",
            ))
            for stmt in module.body()
        )

    def _application_client_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(module.stray_import_violations())
        found.extend(
            self._tesser_import_violations(  # tesser:debt TB051
                module,
                "application client",
                ROLE_TESSER_PACKAGE[PORTS_PARENT_ROLE],
                "an application client module imports only tesser.application",
                "an application client module imports tesser.application exactly once, as ts",
                "an application client module imports tesser.application exactly once, as ts",
            )
        )
        tops = frozenset(each.name().split(".")[0] for each in self._modules)
        spoken = 0
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            pieces = target.split(".")
            if pieces[0] == TESSER:
                continue
            if pieces[0] in tops:
                if pieces[1:3] == [PORTS_PARENT_ROLE, PORTS_PACKAGE] and len(pieces) >= 4:
                    spoken += 1
                    if spoken > 1:
                        found.append(
                            Violation(ViolationSpec(
                                module.path(),
                                lineno,
                                "TB067",
                                f"{module.name()} imports a second ports module {target}; "
                                "an application client module speaks the DTOs of exactly "
                                "one ports module",
                            ))
                        )
                    else:
                        found.extend(self._form_violations(module, edge))  # tesser:debt TB051
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB067",
                        f"{module.name()} imports {target}; an application client module "
                        "speaks the DTOs of exactly one ports module",
                    ))
                )
            elif target not in PORTS_STDLIB and pieces[0] not in PORTS_STDLIB:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB067",
                        f"{module.name()} imports {target}; an application client module "
                        "imports only tesser.application, one ports module, and the pure stdlib",
                    ))
                )
        if spoken == 0 and module.class_defs():
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB067",
                    f"{module.name()} imports no ports module; an application client "
                    "module speaks the DTOs of exactly one ports module",
                ))
            )
        for stmt in module.body():
            if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.ClassDef)):
                continue
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    stmt.lineno,
                    "TB051",
                    f"{module.name()} has a loose module-level statement; "
                    "an application client module holds only imports and classes",
                ))
            )
        protocols: list[ast.ClassDef] = []
        for stmt in module.class_defs():
            where = f"{module.name()}.{stmt.name}"
            block = blocks.get((module.name(), stmt.name))
            if block == "actions_client":
                protocols.append(stmt)
            elif block is None:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB052",
                        f"{where} declares no ts.* base; an application client module "
                        "declares exactly one ts.Client protocol and nothing else",
                    ))
                )
            else:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB052",
                        f"{where} is {KIND_NAME[block]}; an application client module "
                        "declares exactly one ts.Client protocol and nothing else",
                    ))
                )
            for inner in self._nested_class_defs(stmt.body):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        inner.lineno,
                        "TB052",
                        f"{where}.{inner.name} is a nested class; an application client "
                        "module declares its protocol at module level",
                    ))
                )
            found.extend(self._import_time_violations(module, stmt))  # tesser:debt TB051
        if len(protocols) != 1 and module.class_defs():
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    protocols[1].lineno if len(protocols) > 1 else 1,
                    "TB052",
                    f"{module.name()} declares {len(protocols)} client protocols; an "
                    "application client module declares exactly one ts.Client protocol "
                    "and nothing else",
                ))
            )
        return tuple(found)

    def _import_time_violations(
        self, module: Module, stmt: ast.ClassDef
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        where = f"{module.name()}.{stmt.name}"
        members = [
            item
            for item in stmt.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        computed: list[ast.expr] = list(stmt.bases)
        for item in members:
            computed.extend(
                arg.annotation
                for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                if arg.annotation is not None
            )
            if item.returns is not None:
                computed.append(item.returns)
            computed.extend(item.args.defaults)
            computed.extend(value for value in item.args.kw_defaults if value is not None)
        runs = (
            bool(stmt.decorator_list)
            or bool(stmt.keywords)
            or any(item.decorator_list for item in members)
            or any(
                isinstance(inner, (ast.Call, ast.Lambda, ast.Await, ast.NamedExpr))
                or isinstance(
                    inner, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
                )
                for node in computed
                for inner in ast.walk(node)
            )
        )
        if runs:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    stmt.lineno,
                    "TB051",
                    f"{where} runs an expression at import; an application client module "
                    "holds no expression that runs at import, because a job imports it",
                ))
            )
        for held in stmt.body:
            if isinstance(held, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Pass)):
                continue
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    held.lineno,
                    "TB051",
                    f"{where} carries a class-level statement; an application client "
                    "module declares calls and nothing else",
                ))
            )
        return tuple(found)

    def _orchestrators_module_violations(
        self,
        module: Module,
        context: str,
        contexts: frozenset[str],
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(
            self._role_module_violations(  # tesser:debt TB051
                module,
                PORTS_PARENT_ROLE,
                blocks,
                frozenset({"orchestrator", "port_response"}),
            )
        )
        found.extend(
            self._import_violations(  # tesser:debt TB051
                module, context, PORTS_PARENT_ROLE, contexts, blocks
            )
        )
        held = [
            cls
            for cls in module.class_defs()
            if blocks.get((module.name(), cls.name)) == "orchestrator"
        ]
        responses = [
            cls
            for cls in module.class_defs()
            if blocks.get((module.name(), cls.name)) == "port_response"
        ]
        if len(held) != 1 and module.class_defs():
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    held[1].lineno if len(held) > 1 else 1,
                    "TB052",
                    f"{module.name()} declares {len(held)} orchestrators; an orchestrators "
                    "module declares exactly one orchestrator, its mappers, and at most "
                    "its own response",
                ))
            )
        if len(responses) > 1:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    responses[1].lineno,
                    "TB052",
                    f"{module.name()} declares {len(responses)} responses; an orchestrators "
                    "module declares exactly one orchestrator, its mappers, and at most "
                    "its own response",
                ))
            )
        return tuple(found)

    @staticmethod
    def _enum_base(module: Module, stmt: ast.ClassDef) -> str | None:
        for base in stmt.bases:
            if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                if module._package_aliases.get(base.value.id) == ENUM_MODULE:
                    return base.attr
            elif isinstance(base, ast.Name):
                origin = module._imported.get(base.id)
                if origin is not None and origin[0] == ENUM_MODULE:
                    return origin[1]
        return None

    def _names_a_domain_enum(self, module: Module, node: ast.expr | None) -> bool:
        if node is None:
            return False
        for sub in ast.walk(node):
            if isinstance(sub, (ast.Name, ast.Attribute)):
                key = module._resolve(sub)
                if key is not None and key in self._domain_enums:
                    return True
        return False

    @staticmethod
    def _enum_extras(module: Module, stmt: ast.ClassDef) -> tuple[ast.stmt, ...]:
        extras: list[ast.stmt] = []
        for item in stmt.body:
            if isinstance(item, ast.Pass):
                continue
            member_target: ast.expr | None = None
            member_value: ast.expr | None = None
            if isinstance(item, ast.AnnAssign):
                member_target, member_value = item.target, item.value
            elif isinstance(item, ast.Assign) and len(item.targets) == 1:
                member_target, member_value = item.targets[0], item.value
            is_member = (
                isinstance(member_target, ast.Name)
                and not member_target.id.startswith("_")
                and not (
                    isinstance(item, ast.AnnAssign)
                    and not isinstance(item.annotation, ast.Name)
                )
                and (
                    isinstance(member_value, ast.Constant)
                    or (
                        isinstance(member_value, ast.UnaryOp)
                        and isinstance(member_value.operand, ast.Constant)
                        and isinstance(member_value.operand.value, (int, float))
                    )
                    or (
                        member_value is not None
                        and Codebase._is_enum_auto(module, member_value)
                    )
                )
            )
            if not is_member:
                extras.append(item)
        return tuple(extras)

    def _ports_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(module.stray_import_violations())
        found.extend(
            self._tesser_import_violations(  # tesser:debt TB051
                module,
                "ports",
                ROLE_TESSER_PACKAGE[PORTS_PARENT_ROLE],
                "a ports module imports only tesser.application",
                "a ports module imports tesser.application exactly once, as ts",
                "a ports module imports tesser.application exactly once, as ts",
            )
        )
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            head = target.split(".")[0]
            if head == TESSER:
                continue
            if head in (frozenset(each.name().split(".")[0] for each in self._modules)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB067",
                        f"{module.name()} imports {target}; a ports module is a leaf "
                        "and imports nothing from its tree, its own siblings included",
                    ))
                )
            elif target not in PORTS_STDLIB and head not in PORTS_STDLIB:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB067",
                        f"{module.name()} imports {target}; a ports module imports "
                        "only tesser.application and the pure stdlib",
                    ))
                )
        for stmt in module.body():
            if not isinstance(stmt, ast.ClassDef):
                continue
            for inner in self._nested_class_defs(stmt.body):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        inner.lineno,
                        "TB052",
                        f"{module.name()}.{stmt.name}.{inner.name} is a nested class; "
                        "a ports module declares its port and its DTOs at module level, "
                        "where the one-port count can see them",
                    ))
                )
        for stmt in self._nested_class_defs(list(module.body())):
            found.extend(self._decoration_violations(module, stmt.name, stmt))  # tesser:debt TB051
            for keyword in stmt.keywords:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()}.{stmt.name} carries a class keyword; a ports "
                        "module holds no expression that runs at import, and a metaclass "
                        "is logic every adapter imports",
                    ))
                )
            for item in stmt.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for _ in getattr(item, "type_params", ()):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            item.lineno,
                            "TB051",
                            f"{module.name()}.{stmt.name}.{item.name} is generic; a ports "
                            "module names concrete shapes, because a type parameter is a "
                            "slot the shape rules cannot read and a bound is an expression",
                        ))
                    )
                annotations = [arg.annotation for arg in ([
                            arg
                            for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                            if arg.arg != "self"
                        ])] + [item.returns]
                if any((node is not None and any(
                            isinstance(inner, (ast.Call, ast.Lambda, ast.Await, ast.NamedExpr))
                            or isinstance(inner, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
                            for inner in ast.walk(node)
                        )) for node in annotations):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            item.lineno,
                            "TB051",
                            f"{module.name()}.{stmt.name}.{item.name} computes an "
                            "annotation; a ports module holds no expression that runs at "
                            "import, and an annotation is evaluated like any other",
                        ))
                    )
            for _ in getattr(stmt, "type_params", ()):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()}.{stmt.name} is generic; a ports module names "
                        "concrete shapes, because a type parameter is a slot the shape "
                        "rules cannot read and a bound is an expression",
                    ))
                )
            for base in stmt.bases:
                if isinstance(base, (ast.Name, ast.Attribute, ast.Subscript)) and not (
                    (base is not None and any(
                                isinstance(inner, (ast.Call, ast.Lambda, ast.Await, ast.NamedExpr))
                                or isinstance(inner, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
                                for inner in ast.walk(base)
                            ))
                ):
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB051",
                        f"{module.name()}.{stmt.name} computes a base; a ports module "
                        "holds no expression that runs at import, and a base built by a "
                        "call is logic every adapter imports",
                    ))
                )
            for item in stmt.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found.extend(
                        self._decoration_violations(module, f"{stmt.name}.{item.name}", item)  # tesser:debt TB051
                    )
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                    not isinstance(default, ast.Constant)
                    for default in item.args.defaults + [
                        value for value in item.args.kw_defaults if value is not None
                    ]
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            item.lineno,
                            "TB051",
                            f"{module.name()}.{stmt.name}.{item.name} carries a computed "
                            "default; a ports module holds no expression that runs at "
                            "import, because every adapter imports it",
                        ))
                    )
            if self._enum_base(module, stmt) is not None:  # tesser:debt TB051
                for item in self._enum_extras(module, stmt):  # tesser:debt TB051
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            item.lineno,
                            "TB051",
                            f"{module.name()}.{stmt.name} carries more than its members; "
                            "a ports enum is a closed set of names and nothing else, "
                            "because a method or a decorator here is logic every "
                            "adapter imports",
                        ))
                    )
                continue
            for item in stmt.body:
                if isinstance(
                    item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Pass)
                ):
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB051",
                        f"{module.name()}.{stmt.name} carries a class-level statement; "
                        "only an enum member is class-level data in a ports module, "
                        "because anything else runs at import in the one application "
                        "module adapters may import",
                    ))
                )
        ports: list[ast.ClassDef] = []
        stores: list[ast.ClassDef] = []
        for stmt in self._nested_class_defs(list(module.body())):
            block = blocks.get((module.name(), stmt.name))
            where = f"{module.name()}.{stmt.name}"
            enum_base = self._enum_base(module, stmt)  # tesser:debt TB051
            if enum_base is not None and block is None:
                if enum_base not in ENUM_BASES:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is an enum.{enum_base}; a ports enum is an enum.Enum, "
                            "because a str- or int-backed member compares equal to a raw literal "
                            "and reopens the typo the enum closes",
                        ))
                    )
                elif len(stmt.bases) > 1:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} mixes another base into its enum; a ports enum "
                            "subclasses enum.Enum alone, because a str- or int-backed member "
                            "compares equal to a raw literal and reopens the typo the enum closes",
                        ))
                    )
                continue
            if block is None:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB052",
                        f"{where} declares no ts.* base; a ports class declares its block",
                    ))
                )
            elif block not in PORTS_KINDS:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB052",
                        f"{where} is {KIND_NAME[block]}; only a port and the requests "
                        "and responses it speaks live in a ports module",
                    ))
                )
            elif block == "port":
                ports.append(stmt)
            elif block == "store":
                stores.append(stmt)
            if block in ("port_request", "port_response") and any(
                blocks.get((module.name(), base.id)) in ("port_request", "port_response")
                for base in stmt.bases
                if isinstance(base, ast.Name)
            ):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB052",
                        f"{where} subclasses a port DTO; a port DTO is never subclassed, "
                        "because a response hierarchy is a union mypy cannot check for exhaustiveness",
                    ))
                )
        if len(ports) > 1:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    ports[1].lineno,
                    "TB052",
                    f"{module.name()} declares {len(ports)} ports; a ports module "
                    "declares exactly one port, so no two ports can share a request or a response",
                ))
            )
        if len(stores) > 1:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    stores[1].lineno,
                    "TB052",
                    f"{module.name()} declares {len(stores)} stores; a ports module "
                    "declares at most one store, which yields the one port beside it",
                ))
            )
        if stores and not ports:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    stores[0].lineno,
                    "TB052",
                    f"{module.name()} declares a store and no port; a store yields the "
                    "repository its transaction binds, declared in its own ports module",
                ))
            )
        if not ports and not stores and self._nested_class_defs(list(module.body())):
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB052",
                    f"{module.name()} declares no port; a ports module "
                    "declares exactly one port, so no two ports can share a request or a response",
                ))
            )
        for stmt in module.body():
            if isinstance(stmt, (ast.Import, ast.ImportFrom, ast.ClassDef)):
                continue
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    stmt.lineno,
                    "TB051",
                    f"{module.name()} has a loose module-level statement; "
                    "a ports module holds only imports and classes",
                ))
            )
        for loose in module.body():
            if isinstance(loose, (ast.Import, ast.ImportFrom, ast.ClassDef)):
                continue
            found.extend(self._unreadable(module, module.name(), loose))  # tesser:debt TB051
        for holder in module.class_defs():
            enum_member = self._enum_base(module, holder) is not None  # tesser:debt TB051
            enum_extras = frozenset(map(id, self._enum_extras(module, holder)))  # tesser:debt TB051
            for base in holder.bases:
                if not self._is_readable_annotation(base):
                    found.extend(
                        self._unreadable(module, f"{module.name()}.{holder.name}", base)  # tesser:debt TB051
                    )
            for item in holder.body:
                where = f"{module.name()}.{holder.name}"
                if isinstance(item, ast.Pass):
                    continue
                if enum_member:
                    if id(item) in enum_extras:
                        found.extend(self._unreadable(module, where, item))  # tesser:debt TB051
                    continue
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found.extend(self._unreadable(module, where, item))  # tesser:debt TB051
                    continue
                shape = f"{where}.{item.name}"
                for node in [arg.annotation for arg in ([
                            arg
                            for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                            if arg.arg != "self"
                        ])] + [
                    item.returns
                ]:
                    if node is not None and not self._is_readable_annotation(node):
                        found.extend(self._unreadable(module, shape, node))  # tesser:debt TB051
                for body_stmt in item.body:
                    if isinstance(
                        body_stmt, (ast.Pass, ast.Return, ast.Assign, ast.AnnAssign)
                    ):
                        continue
                    if (
                        isinstance(body_stmt, ast.Expr)
                        and isinstance(body_stmt.value, ast.Constant)
                        and body_stmt.value.value is Ellipsis
                    ):
                        continue
                    found.extend(self._unreadable(module, shape, body_stmt))  # tesser:debt TB051
        return tuple(found)

    @staticmethod
    def _decoration_violations(
        module: Module, where: str, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
    ) -> tuple[Violation, ...]:
        return tuple(
            Violation(ViolationSpec(
                module.path(),
                node.lineno,
                "TB051",
                f"{module.name()}.{where} is decorated; a ports module holds no "
                "decorator, because a decorator is a call that runs at import in the "
                "one application module adapters may import",
            ))
            for _ in node.decorator_list
        )

    @classmethod
    def _is_readable_annotation(cls, node: ast.expr) -> bool:
        if isinstance(node, ast.Constant):
            return node.value is None or node.value is Ellipsis
        if isinstance(node, ast.Name):
            return True
        if isinstance(node, ast.Attribute):
            return cls._is_readable_annotation(node.value)
        if isinstance(node, ast.Subscript):
            inner = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            return cls._is_readable_annotation(node.value) and all(
                cls._is_readable_annotation(element) for element in inner
            )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return cls._is_readable_annotation(node.left) and cls._is_readable_annotation(
                node.right
            )
        return False

    @staticmethod
    def _unreadable(module: Module, where: str, node: ast.AST) -> tuple[Violation, ...]:
        return (
            Violation(ViolationSpec(
                module.path(),
                getattr(node, "lineno", 1),
                "TB069",
                f"{where} holds a {type(node).__name__}; a ports module holds only the "
                "shapes its rules can read, so anything else is a finding by default "
                "rather than a gap nobody enumerated",
            )),
        )

    def _role_module_violations(
        self,
        module: Module,
        role: str,
        blocks: dict[tuple[str, str], str],
        extra: frozenset[str] = frozenset(),
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        parts = module.name().split(".")
        kind_package = parts[2] if len(parts) >= 4 else None
        if role == "adapters" and kind_package not in ADAPTER_KIND_PACKAGES:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB041",
                    f"{module.name()} is not in an adapter kind package; an adapters "
                    "module lives in handlers, gateways, repositories, or jobs, because "
                    "placement is what carries an adapter's reach",
                ))
            )
        for stmt in module.body():
            if isinstance(stmt, ast.ClassDef):
                block = blocks.get((module.name(), stmt.name))
                where = f"{module.name()}.{stmt.name}"
                enum_base = self._enum_base(module, stmt)  # tesser:debt TB051
                if enum_base is not None and block is None and role == "domain":
                    if enum_base not in ENUM_BASES:
                        found.append(
                            Violation(ViolationSpec(
                                module.path(),
                                stmt.lineno,
                                "TB052",
                                f"{where} is an enum.{enum_base}; a domain enum is an enum.Enum, "
                                "because a str- or int-backed member compares equal to a raw literal "
                                "and reopens the typo the enum closes",
                            ))
                        )
                    elif len(stmt.bases) > 1:
                        found.append(
                            Violation(ViolationSpec(
                                module.path(),
                                stmt.lineno,
                                "TB052",
                                f"{where} mixes another base into its enum; a domain enum "
                                "subclasses enum.Enum alone, because a str- or int-backed member "
                                "compares equal to a raw literal and reopens the typo the enum closes",
                            ))
                        )
                    else:
                        if stmt.decorator_list or stmt.keywords:
                            found.append(
                                Violation(ViolationSpec(
                                    module.path(),
                                    stmt.lineno,
                                    "TB051",
                                    f"{where} is decorated or keyworded; "
                                    "a domain enum is a bare class statement, "
                                    "because a decorator or a metaclass rewrites "
                                    "the primitive into a home for behavior",
                                ))
                            )
                        for item in self._enum_extras(module, stmt):  # tesser:debt TB051
                            found.append(
                                Violation(ViolationSpec(
                                    module.path(),
                                    item.lineno,
                                    "TB051",
                                    f"{where} carries more than its members; "
                                    "a domain enum is a closed set of names and nothing else, "
                                    "because an enum is a primitive with a name, "
                                    "not a home for behavior",
                                ))
                            )
                    continue
                if block is None:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} declares no ts.* base; every context class declares its block",
                        ))
                    )
                elif block in SRV_KINDS:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}; "
                            "a host lives in srv and a protocol kind in a protocol module, never a context",
                        ))
                    )
                elif KIND_ROLE[block] != role and block not in extra:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB052",
                            f"{where} is {KIND_NAME[block]}, whose home is {KIND_HOME[block]}; "
                            "a kind lives only in its role module",
                        ))
                    )
        found.extend(
            self._module_function_violations(module, "context role")  # tesser:debt TB051
        )
        found.extend(
            self._statement_violations(  # tesser:debt TB051
                module,
                "module",
                "a context module holds only imports, classes, and Final constants",
                None,
            )
        )
        if role == "adapters":
            kinds = {
                blocks.get((module.name(), cls.name)) for cls in module.class_defs()
            } & ADAPTER_BLOCKS
            if len(kinds) > 1:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        1,
                        "TB052",
                        f"{module.name()} mixes adapter kinds; an adapters module holds one adapter kind",
                    ))
                )
            expected = ADAPTER_KIND_PACKAGES.get(kind_package or "", frozenset())
            for cls in module.class_defs():
                block = blocks.get((module.name(), cls.name))
                if block is None or block not in ADAPTER_BLOCKS or block in expected:
                    continue
                if not expected:
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        cls.lineno,
                        "TB052",
                        f"{module.name()}.{cls.name} is {KIND_NAME[block]}, and its "
                        "package names another kind; an adapters module holds the kind "
                        "of its kind package, because the package is what carries its reach",
                    ))
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
        found.extend(module.stray_import_violations())
        own = module.name().split(".")
        kind_package = own[2] if len(own) >= 4 and own[1] == "adapters" else None
        kind_reach = ADAPTER_KIND_REACH.get(kind_package or "")
        holds_gateway = (module is not None and any(
                    blocks.get((module.name(), cls.name)) == ("gateway") for cls in module.class_defs()
                ))
        if role == "domain":
            found.extend(
                self._tesser_import_violations(  # tesser:debt TB051
                    module,
                    "role",
                    ROLE_TESSER_PACKAGE[role],
                    "a domain module's tesser imports are tesser.domain, "
                    "tesser.errors, and tesser.serialization",
                    "a role module imports its tesser package exactly once, as ts",
                    "a role module imports its tesser package exactly once, as ts",
                    NORM_IMPORTS[role],
                )
            )
        elif role == "application":
            found.extend(
                self._tesser_import_violations(  # tesser:debt TB051
                    module,
                    "role",
                    ROLE_TESSER_PACKAGE[role],
                    "an application module's tesser imports are "
                    "tesser.application and tesser.errors",
                    "a role module imports its tesser package exactly once, as ts",
                    "a role module imports its tesser package exactly once, as ts",
                    NORM_IMPORTS[role],
                )
            )
        elif role == "adapters":
            found.extend(
                self._tesser_import_violations(  # tesser:debt TB051
                    module,
                    "role",
                    ROLE_TESSER_PACKAGE[role],
                    "an adapters module's tesser imports are "
                    "tesser.adapters and tesser.errors",
                    "a role module imports its tesser package exactly once, as ts",
                    "a role module imports its tesser package exactly once, as ts",
                    NORM_IMPORTS[role],
                )
            )
        elif role == "component":
            found.extend(
                self._tesser_import_violations(  # tesser:debt TB051
                    module,
                    "role",
                    ROLE_TESSER_PACKAGE[role],
                    "a component module's tesser imports are tesser.component, "
                    "and tesser.errors",
                    "a role module imports its tesser package exactly once, as ts",
                    "a role module imports its tesser package exactly once, as ts",
                    NORM_IMPORTS[role],
                )
            )
        else:
            found.extend(
                self._tesser_import_violations(  # tesser:debt TB051
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
                inner = ".".join(pieces[1:])
                job_only = any(
                    inner == entry or inner.startswith(f"{entry}.")
                    for entry in JOB_ONLY_IMPORTS
                )
                if pieces[0] == context and job_only and kind_package != "jobs":
                    denied.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB060",
                            f"{module.name()} imports {target}; only a job imports the "
                            "application client and the orchestrators, because an action "
                            "is reachable only through the engine",
                        ))
                    )
                elif pieces[0] == context and role == "adapters" and kind_reach is not None:
                    if not any(
                        inner == allowed or inner.startswith(f"{allowed}.")
                        for allowed in kind_reach + (f"adapters.{kind_package}",)
                    ):
                        denied.append(
                            Violation(ViolationSpec(
                                module.path(),
                                lineno,
                                "TB060",
                                f"{module.name()} imports {target}; an adapters kind "
                                "package reaches only what its kind reaches — a handler "
                                "the context client, a job the application client, the "
                                "orchestrators, and the ports, a gateway or a repository "
                                "the ports",
                            ))
                        )
                elif pieces[0] == context:
                    if not (
                        len(pieces) >= 2
                        and (
                            pieces[1] == role
                            or any(
                                inner == allowed or inner.startswith(f"{allowed}.")
                                for allowed in SAME_CONTEXT_IMPORTS[role]
                            )
                        )
                    ):
                        denied.append(
                            Violation(ViolationSpec(
                                module.path(),
                                lineno,
                                "TB060",
                                f"{module.name()} imports {target}; the same-context matrix is "
                                "a role to itself, application to domain and client, adapters to "
                                "application/ports, component to application, adapters, and client",
                            ))
                        )
                elif tail != "client" or not (role == "component" or (role == "adapters" and holds_gateway)):
                    denied.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB061",
                            f"{module.name()} imports {target}; a context reaches another context "
                            "only through its client, and only from gateways and components",
                        ))
                    )
                found.extend(denied)
                if not denied:
                    found.extend(self._form_violations(module, edge))  # tesser:debt TB051
            elif pieces[0] in ((
                        frozenset({KERNEL_PACKAGE})
                        | (frozenset({self._export}) if self._export is not None else frozenset())
                    ) & frozenset(each.name().split(".")[0] for each in self._modules)) and (any(
                        module.name() == target or module.name().startswith(target + ".")
                        for module in self._modules
                    )):
                continue
            else:
                covered = False
                for declared in self._imports:
                    if target == declared or target.startswith(declared + "."):
                        self._used_imports.add(declared)
                        covered = True
                        break
                if covered:
                    continue
                if role in CORE_STDLIB and not (
                    self._pure_domain_import(target)  # tesser:debt TB051
                    if role == "domain"
                    else (target in CORE_STDLIB[role] or pieces[0] in CORE_STDLIB[role])
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB062",
                            f"{module.name()} imports {target}; domain, client, and application "
                            "import only their context, their kernels, their tesser package, "
                            "and the pure stdlib",
                        ))
                    )
                elif (
                    pieces[0] in SHELL_PACKAGES
                    and pieces[0] in (frozenset(each.name().split(".")[0] for each in self._modules))
                    and not (
                        role == "adapters"
                        and pieces[0] == PROTOCOL_PACKAGE
                        and len(module.name().split(".")) >= 3
                        and module.name().split(".")[2] == "handlers"
                    )
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB066",
                            f"{module.name()} imports {target}; of the app shell a context "
                            "imports only protocol, and only from its handlers",
                        ))
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
                imported = next(
                    (named for named in self._modules if named.name() == target), None
                )
                if package == "srv" and not (
                    tail == "adapters"
                    and (imported is not None and any(
                                blocks.get((imported.name(), cls.name)) in HOST_KINDS for cls in imported.class_defs()
                            ))
                ):
                    denied.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB063",
                            f"{module.name()} imports {target}; "
                            "a host reaches a context only through its handlers and its jobs",
                        ))
                    )
                elif package == "app" and tail not in ("component", "client", "adapters"):
                    denied.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB063",
                            f"{module.name()} imports {target}; an app builds from "
                            "components, clients, and adapters, never domain or application",
                        ))
                    )
                found.extend(denied)
                if not denied:
                    found.extend(self._form_violations(module, edge))  # tesser:debt TB051
            elif package == "app" and pieces[0] == "srv":
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB063",
                        f"{module.name()} imports {target}; the composition root never imports a host",
                    ))
                )
            elif pieces[0] == TESTS_ROLE and pieces[0] in (frozenset(each.name().split(".")[0] for each in self._modules)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB066",
                        f"{module.name()} imports {target}; "
                        "production code never imports the tests package",
                    ))
                )
            elif package == "app" and pieces[0] == PROTOCOL_PACKAGE:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB066",
                        f"{module.name()} imports {target}; "
                        "an app composes the application and never imports protocol",
                    ))
                )
        return tuple(found)

    def _shell_reach_violations(self, module: Module, tier: str) -> tuple[Violation, ...]:
        allowed = TEST_TIER_SHELL[tier]
        tops = (frozenset(each.name().split(".")[0] for each in self._modules))
        found: list[Violation] = []
        for edge in module.import_edges():
            target = str(edge._target)
            lineno = int(edge._lineno)
            top = target.split(".")[0]
            if top not in SHELL_PACKAGES or top not in tops or top in allowed:
                continue
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    lineno,
                    "TB070",
                    f"{module.name()} imports {target}, but a test placed in {tier} "
                    "does not reach that package; "
                    "a test reaches only what its placement allows",
                ))
            )
        return tuple(found)

    def _test_placement_violations(
        self,
        module: Module,
        context: str,
        tier: str,
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        if tier == STRAY_TIER:
            return (
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB070",
                    f"{module.name()} resolves to no test tier; "
                    "a sibling test lives in a role package, an adapter kind package "
                    "(handlers, gateways, repositories, jobs), or the orchestrators package",
                )),
            )
        found.extend(self._shell_reach_violations(module, tier))  # tesser:debt TB051
        if tier == ROOT_TESTS_TIER:
            for edge in module.import_edges():
                target = str(edge._target)
                lineno = int(edge._lineno)
                pieces = target.split(".")
                if pieces[0] not in contexts:
                    continue
                if len(pieces) >= 2 and pieces[1] in ("component", "client"):
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        "the root tests package reaches a context only through its "
                        "component and client; "
                        "a test reaches only what its placement allows",
                    ))
                )
            return tuple(found)
        if tier == KERNEL_TIER:
            for edge in module.import_edges():
                target = str(edge._target)
                lineno = int(edge._lineno)
                pieces = target.split(".")
                if pieces[0] not in contexts:
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        "a kernel reaches no context; "
                        "a test reaches only what its placement allows",
                    ))
                )
            return tuple(found)
        if tier == SRV_TIER:
            for edge in module.import_edges():
                target = str(edge._target)
                lineno = int(edge._lineno)
                pieces = target.split(".")
                if pieces[0] not in contexts:
                    continue
                if len(pieces) >= 3 and pieces[1] == "adapters" and pieces[2] in ("handlers", "jobs"):
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        "srv reaches a context only through its handlers and its jobs; "
                        "a test reaches only what its placement allows",
                    ))
                )
            return tuple(found)
        if tier == APP_TIER:
            for edge in module.import_edges():
                target = str(edge._target)
                lineno = int(edge._lineno)
                pieces = target.split(".")
                if pieces[0] not in contexts:
                    continue
                if len(pieces) >= 2 and pieces[1] in ("component", "client", "adapters"):
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        "an app reaches a context only through its component, client, "
                        "and adapters; "
                        "a test reaches only what its placement allows",
                    ))
                )
            return tuple(found)
        if tier == PROTOCOL_TIER:
            for edge in module.import_edges():
                target = str(edge._target)
                lineno = int(edge._lineno)
                pieces = target.split(".")
                if pieces[0] not in contexts:
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        "protocol reaches no context; "
                        "a test reaches only what its placement allows",
                    ))
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
                inner = ".".join(pieces[1:])
                allowed = any(
                    inner == entry or inner.startswith(f"{entry}.") for entry in reach
                )
                if not allowed and home is not None and tail == home[0]:
                    allowed = home[1] is None or (len(pieces) >= 3 and pieces[2] == home[1])
                at_home = (
                    home is not None
                    and home[1] is not None
                    and tail == home[0]
                    and len(pieces) >= 3
                    and pieces[2] == home[1]
                )
                if allowed and tier != "jobs" and not at_home and any(
                    inner == entry or inner.startswith(f"{entry}.")
                    for entry in JOB_ONLY_IMPORTS
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB070",
                            f"{module.name()} imports {target}, but only a test placed in "
                            "jobs reaches the application client and the orchestrators; "
                            "a test reaches only what its placement allows",
                        ))
                    )
                elif not allowed:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            lineno,
                            "TB070",
                            f"{module.name()} imports {target}, but a test placed in "
                            f"{tier} reaches only {own_roles} of its own context; "
                            "a test reaches only what its placement allows",
                        ))
                    )
            elif not foreign:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        f"{tier} reaches no neighbouring context; "
                        "a test reaches only what its placement allows",
                    ))
                )
            elif tail not in foreign:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        lineno,
                        "TB070",
                        f"{module.name()} imports {target}, but a test placed in "
                        f"{tier} reaches only {foreign_roles} of a neighbouring context; "
                        "a test reaches only what its placement allows",
                    ))
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
                Violation(ViolationSpec(
                    module.path(),
                    1,
                    "TB070",
                    f"{module.name()} is an eval outside a gateway; "
                    "an eval lives only in a gateway, the one place a sampled real-model "
                    "call is honest",
                )),
            )
        return self._test_module_violations(module, blocks, contexts)  # tesser:debt TB051

    def _test_module_violations(
        self,
        module: Module,
        blocks: dict[tuple[str, str], str],
        contexts: frozenset[str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        found.extend(module.stray_import_violations())
        tier_parts = module.name().split(".")
        tier_tops = (
            frozenset({KERNEL_PACKAGE})
            | (frozenset({self._export}) if self._export is not None else frozenset())
        ) & frozenset(each.name().split(".")[0] for each in self._modules)
        if tier_parts[0] in tier_tops and len(tier_parts) >= 2:
            placement: tuple[str, str] | None = ("", KERNEL_TIER)
        elif tier_parts[0] == "srv" and len(tier_parts) >= 2:
            placement = ("", SRV_TIER)
        elif tier_parts[0] == "app" and len(tier_parts) >= 2:
            placement = ("", APP_TIER)
        elif tier_parts[0] == PROTOCOL_PACKAGE and len(tier_parts) >= 2:
            placement = ("", PROTOCOL_TIER)
        elif tier_parts[0] == TESTS_ROLE and len(tier_parts) >= 2:
            placement = ("", ROOT_TESTS_TIER)
        elif len(tier_parts) < 3 or tier_parts[0] not in contexts:
            placement = None
        elif tier_parts[1] == TESTS_ROLE:
            placement = (tier_parts[0], TESTS_ROLE)
        elif tier_parts[1] not in ROLES:
            placement = (tier_parts[0], STRAY_TIER)
        elif tier_parts[1] == "adapters":
            placement = (
                (tier_parts[0], tier_parts[2])
                if len(tier_parts) >= 4 and tier_parts[2] in ADAPTER_TEST_TIERS
                else (tier_parts[0], STRAY_TIER)
            )
        elif (
            tier_parts[1] == PORTS_PARENT_ROLE
            and len(tier_parts) >= 4
            and tier_parts[2] == ORCHESTRATORS_PACKAGE
        ):
            placement = (tier_parts[0], ORCHESTRATORS_PACKAGE)
        else:
            placement = (tier_parts[0], tier_parts[1])
        if placement is None:
            placement = ("", STRAY_TIER)
        found.extend(self._test_placement_violations(module, placement[0], placement[1], contexts))  # tesser:debt TB051
        for edge in module.import_edges():
            if str(edge._target).split(".")[0] in contexts:
                found.extend(self._form_violations(module, edge))  # tesser:debt TB051
        if self._export != TESSER:
            found.extend(
                self._tesser_import_violations(  # tesser:debt TB051
                    module,
                    "test",
                    "tesser.testing",
                    "a test module's tesser imports are tesser.testing, "
                    "tesser.errors, and tesser.serialization",
                    "a test module imports tesser.testing at most once, as ts",
                    None,
                    NORM_IMPORTS["test"],
                )
            )
        for stmt in module.body():
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                where = f"{module.name()}.{stmt.name}"
                if stmt.name.startswith("test_"):
                    continue
                if (any(
                            key is not None and TESSER_DECORATORS.get(key) == ("helper")
                            for key in (module._resolve(decorator) for decorator in stmt.decorator_list)
                        )):
                    found.extend(self._helper_violations(module, where, stmt.lineno, stmt, blocks))  # tesser:debt TB051
                    continue
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB071",
                        f"{where} is neither a test nor a declared helper; a test module holds "
                        "tests, @ts.helper builders, and @ts.fake doubles",
                    ))
                )
            elif isinstance(stmt, ast.ClassDef):
                if self._export == TESSER:
                    continue
                where = f"{module.name()}.{stmt.name}"
                if not (any(
                            key is not None and TESSER_DECORATORS.get(key) == ("fake")
                            for key in (module._resolve(decorator) for decorator in stmt.decorator_list)
                        )):
                    if stmt.name.startswith("Test"):
                        for item in stmt.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                if not item.name.startswith("test_"):
                                    found.append(
                                        Violation(ViolationSpec(
                                            module.path(),
                                            item.lineno,
                                            "TB071",
                                            f"{where}.{item.name} is not a test method; a test class holds only test methods",
                                        ))
                                    )
                            elif isinstance(item, ast.ClassDef):
                                found.append(
                                    Violation(ViolationSpec(
                                        module.path(),
                                        item.lineno,
                                        "TB071",
                                        f"{where}.{item.name} is a nested class; a test class holds test methods, never nested classes",
                                    ))
                                )
                            else:
                                found.append(
                                    Violation(ViolationSpec(
                                        module.path(),
                                        item.lineno,
                                        "TB071",
                                        f"{where} carries a loose statement in its body; a test class holds test methods, never loose statements",
                                    ))
                                )
                        continue
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB072",
                            f"{where} is an undeclared class; a class in a test module is a Test-prefixed test class or declares itself with @ts.fake",
                        ))
                    )
                elif not any(
                    blocks.get(key)
                    in (
                        "port",
                        "store",
                        "client",
                        "actions_client",
                        "job_context",
                        "protocol_port",
                        "config_repository",
                    )
                    for key in (module._resolve(base) for base in stmt.bases)
                    if key is not None
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stmt.lineno,
                            "TB072",
                            f"{where} implements no application port, store, protocol port, "
                            "client, or config repository; a fake implements the contract it doubles",
                        ))
                    )
            else:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        stmt.lineno,
                        "TB071",
                        f"{module.name()} has a loose module-level statement; "
                        "a test module holds only imports, tests, helpers, and fakes",
                    ))
                )
        return tuple(found)

    def _helper_violations(
        self,
        module: Module,
        where: str,
        line: int,
        fn: ast.FunctionDef | ast.AsyncFunctionDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        params = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
        for arg in params:
            if not self._allowed_annotation(module, arg.annotation, blocks, frozenset()):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        line,
                        "TB073",
                        f"{where} parameter {arg.arg!r} is not a primitive; "
                        "a helper takes only defaulted primitives",
                    ))
                )
        positional = fn.args.posonlyargs + fn.args.args
        undefaulted = positional[: len(positional) - len(fn.args.defaults)]
        missing = [arg for arg in undefaulted] + [
            arg for arg, default in zip(fn.args.kwonlyargs, fn.args.kw_defaults) if default is None
        ]
        for arg in missing:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    line,
                    "TB073",
                    f"{where} parameter {arg.arg!r} has no default; "
                    "a helper takes only defaulted primitives",
                ))
            )
        helper_key = module._resolve(fn.returns) if fn.returns is not None else None
        if helper_key is not None and blocks.get(helper_key) == "mapper":
            helper_key = self._mapper_target.get(helper_key)
        if (blocks.get(helper_key) if helper_key is not None else None) not in DATA_BLOCKS:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    line,
                    "TB073",
                    f"{where} returns no construction data; a helper builds a spec or a DTO",
                ))
            )
        for node in ast.walk(fn):
            if isinstance(node, (ast.If, ast.Match, ast.For, ast.While, ast.Try)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        node.lineno,
                        "TB073",
                        f"{where} has control flow; a helper only constructs",
                    ))
                )
        return tuple(found)

    def _valueobject_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        init = (next(
                    (
                        item
                        for item in cls.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"
                    ),
                    None,
                ))
        if init is None:
            return (
                Violation(ViolationSpec(
                    module.path(),
                    cls.lineno,
                    "TB080",
                    f"{module.name()}.{cls.name} defines no __init__; "
                    "a value object constructs in its own __init__",
                )),
            )
        where = f"{module.name()}.{cls.name}.__init__"
        if init.args.vararg is not None or init.args.kwarg is not None:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    init.lineno,
                    "TB080",
                    f"{where} uses *args/**kwargs; "
                    "a value object declares its construction data as named parameters",
                ))
            )
        params = (init.args.posonlyargs + init.args.args)[1:] + init.args.kwonlyargs
        if len(params) != 1 and init.args.vararg is None and init.args.kwarg is None:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    init.lineno,
                    "TB080",
                    f"{where} takes {len(params)} parameters; "
                    "a value object takes one primitive or exactly one ts.Spec",
                ))
            )
        for arg in params:
            plain = self._allowed_annotation(module, arg.annotation, blocks, frozenset(), domain_enums=True)
            taken = self._spec_key(module, arg.annotation, blocks)
            exact = (
                taken is not None
                and taken.shape() == SPEC_ONE
                and isinstance(self._unquoted(arg.annotation), (ast.Name, ast.Attribute))  # tesser:debt TB051
            )
            if not (plain or exact):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        init.lineno,
                        "TB080",
                        f"{where} parameter {arg.arg!r} is not allowed; "
                        "a value object constructs from one primitive or one spec, never value objects",
                    ))
                )
        return tuple(found)

    def _spec_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        init_seen = False
        for item in cls.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{module.name()}.{cls.name} carries a class-level statement; "
                        "a spec declares its fields as __init__ parameters, "
                        "where the field rules can read them",
                    ))
                )
                continue
            where = f"{module.name()}.{cls.name}.{item.name}"
            if item.name != "__init__":
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{where} defines a method on a spec; a spec only carries construction data",
                    ))
                )
                continue
            init_seen = True
            if item.args.vararg is not None or item.args.kwarg is not None:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{where} uses *args/**kwargs; a spec declares its fields "
                        "as named __init__ parameters, where the field rules can read them",
                    ))
                )
            for arg in ([
                        arg
                        for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                        if arg.arg != "self"
                    ]):
                if not self._allowed_annotation(module, arg.annotation, blocks, frozenset({"spec"}), domain_enums=True):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            item.lineno,
                            "TB080",
                            f"{where} parameter {arg.arg!r} is not allowed; "
                            "a spec field is a primitive or a child spec, never a value object",
                        ))
                    )
        if not init_seen:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    cls.lineno,
                    "TB080",
                    f"{module.name()}.{cls.name} defines no __init__; "
                    "a spec defines the __init__ that carries its fields",
                ))
            )
        return tuple(found)

    def _dto_violations(
        self,
        module: Module,
        cls: ast.ClassDef,
        blocks: dict[tuple[str, str], str],
    ) -> tuple[Violation, ...]:
        found: list[Violation] = []
        own = blocks.get((module.name(), cls.name))
        port_dto = own in ("port_request", "port_response")
        nested = (
            frozenset({"port_request", "port_response"})
            if port_dto
            else frozenset({"request", "response"})
        )
        named_enums: set[str] = set()
        if port_dto:
            for enum_stmt in module.class_defs():
                if self._enum_base(module, enum_stmt) is not None:  # tesser:debt TB051
                    named_enums.add(enum_stmt.name)
        enums = frozenset(named_enums)
        for item in cls.body:
            if port_dto and not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{module.name()}.{cls.name} carries a class-level statement; "
                        "a port DTO declares its fields as __init__ parameters, "
                        "where the field rules can read them",
                    ))
                )
                continue
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            where = f"{module.name()}.{cls.name}.{item.name}"
            if item.name == "__init__" and (
                item.args.vararg is not None or item.args.kwarg is not None
            ):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{where} uses *args/**kwargs; a DTO declares its fields "
                        "as named __init__ parameters, where the field rules can read them",
                    ))
                )
            if item.name != "__init__":
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{where} defines a method on a DTO; a DTO carries data and nothing else",
                    ))
                )
                continue
            carrier = True
            if port_dto:
                assignable = frozenset(arg.arg for arg in ([
                            arg
                            for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                            if arg.arg != "self"
                        ]))
                for stmt in item.body:
                    if isinstance(stmt, ast.Return) and (
                        stmt.value is None
                        or (
                            isinstance(stmt.value, ast.Constant)
                            and stmt.value.value is None
                        )
                    ):
                        continue
                    target: ast.expr | None = None
                    assigned: ast.expr | None = None
                    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                        target, assigned = stmt.targets[0], stmt.value
                    elif isinstance(stmt, ast.AnnAssign):
                        target, assigned = stmt.target, stmt.value
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                        and isinstance(assigned, ast.Name)
                        and assigned.id in assignable
                    ):
                        continue
                    carrier = False
                    break
            if port_dto and not carrier:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{where} carries logic; a port DTO constructor only assigns its "
                        "parameters, because a ports module holds no logic to import",
                    ))
                )
            for arg in ([
                        arg
                        for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                        if arg.arg != "self"
                    ]):
                if self._names_bool(arg.annotation):  # tesser:debt TB051
                    if port_dto:
                        found.append(
                            Violation(ViolationSpec(
                                module.path(),
                                item.lineno,
                                "TB080",
                                f"{where} field {arg.arg!r} is a bool; a port DTO field is "
                                "never a bare bool — model the outcome as an enum",
                            ))
                        )
                    else:
                        found.append(
                            Violation(ViolationSpec(
                                module.path(),
                                item.lineno,
                                "TB080",
                                f"{where} field {arg.arg!r} is a bool; a client DTO field is "
                                "never a bare bool — a closed set crosses as its canonical string",
                            ))
                        )
                    continue
                if port_dto and self._is_union(arg.annotation):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            item.lineno,
                            "TB080",
                            f"{where} field {arg.arg!r} is a union; a port DTO field "
                            "is never a union, optional included — model the outcome as an enum",
                        ))
                    )
                    continue
                if not self._allowed_annotation(
                    module,
                    arg.annotation,
                    blocks,
                    nested,
                    enums,
                    PORT_DTO_PRIMITIVES if port_dto else PRIMITIVES,
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            item.lineno,
                            "TB080",
                            f"{where} parameter {arg.arg!r} is not allowed; "
                            "a DTO field is a primitive or another DTO",
                        ))
                    )
        return tuple(found)

    def _mapper_violations(
        self, module: Module, cls: ast.ClassDef, blocks: dict[tuple[str, str], str]
    ) -> tuple[Violation, ...]:
        where = f"{module.name()}.{cls.name}"
        found: list[Violation] = []
        if not cls.name.startswith(MAPPER_PREFIX):
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    cls.lineno,
                    "TB080",
                    f"{where} does not start with MapTo; a mapper is named for "
                    "what it maps to, because its parameters already say what it maps from",
                ))
            )
        target = self._mapper_target.get((module.name(), cls.name))
        if target is None:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    cls.lineno,
                    "TB080",
                    f"{where} is not its target; a mapper subclasses ts.Mapper and then "
                    "the one spec or DTO it maps to, so constructing the mapper constructs the target",
                ))
            )
        else:
            target_name = target[1]
            if target_name not in cls.name:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        cls.lineno,
                        "TB080",
                        f"{where} does not name {target_name}; a mapper is named "
                        "MapTo plus its target, so the reader knows what the constructor yields",
                    ))
                )
        if cls.decorator_list or cls.keywords:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    cls.lineno,
                    "TB080",
                    f"{where} declares a decorator or a class keyword; a mapper is a plain "
                    "class, because a metaclass or decorator can replace the constructor "
                    "that is the mapping",
                ))
            )
        inits = [
            item
            for item in cls.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"
        ]
        init = inits[-1] if inits else None
        if init is None:
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    cls.lineno,
                    "TB080",
                    f"{where} has no __init__; a mapper's constructor is the mapping, so "
                    "without one the target's own constructor is exposed",
                ))
            )
        else:
            if isinstance(init, ast.AsyncFunctionDef):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        init.lineno,
                        "TB080",
                        f"{where}.__init__ is async; a mapper's constructor runs the mapping "
                        "when it is called, and a coroutine never does",
                    ))
                )
            if len(inits) > 1:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        init.lineno,
                        "TB080",
                        f"{where} defines __init__ {len(inits)} times; a mapper has one "
                        "constructor, because the last definition silently wins",
                    ))
                )
            if init.decorator_list:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        init.lineno,
                        "TB080",
                        f"{where}.__init__ is decorated; a mapper's constructor is plain, "
                        "because a decorator can replace the mapping",
                    ))
                )
            if init.args.vararg is not None or init.args.kwarg is not None:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        init.lineno,
                        "TB080",
                        f"{where}.__init__ uses *args or **kwargs; a mapper names each "
                        "whole object it takes",
                    ))
                )
            def primitive_leaf(node: ast.expr) -> bool:
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    try:
                        node = ast.parse(node.value, mode="eval").body
                    except SyntaxError:
                        return False
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                    return primitive_leaf(node.left) or primitive_leaf(node.right)
                if isinstance(node, ast.Subscript):
                    head = self._annotation_head(node)  # tesser:debt TB051
                    inner = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
                    if head in ("Callable", "Literal", "type", "Type"):
                        return False
                    if head in ("dict", "Dict", "Mapping", "MutableMapping"):
                        inner = inner[-1:]
                    return any(primitive_leaf(each) for each in inner)
                return self._annotation_head(node) in PRIMITIVES  # tesser:debt TB051

            for arg in (
                list(init.args.posonlyargs) + list(init.args.args) + list(init.args.kwonlyargs)
            ):
                if arg.arg == "self":
                    continue
                if arg.annotation is None:
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            arg.lineno,
                            "TB080",
                            f"{where} parameter {arg.arg!r} has no annotation; a mapper names "
                            "the whole object it takes",
                        ))
                    )
                    continue
                if primitive_leaf(arg.annotation):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            arg.lineno,
                            "TB080",
                            f"{where} parameter {arg.arg!r} is a primitive; a mapper takes "
                            "whole objects, never a field already pulled off one",
                        ))
                    )
            supers = sum(
                1
                for stmt in init.body
                if isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute)
                and stmt.value.func.attr == "__init__"
                and isinstance(stmt.value.func.value, ast.Call)
                and isinstance(stmt.value.func.value.func, ast.Name)
                and stmt.value.func.value.func.id == "super"
            )
            for returned in self._own_scope_returns(init):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        returned.lineno,
                        "TB080",
                        f"{where}.__init__ returns; a mapper's constructor runs to its "
                        "super().__init__, so the target is always initialized",
                    ))
                )
            selves = {"self"}
            grew = True
            while grew:
                grew = False
                for node in ast.walk(init):
                    if (
                        isinstance(node, (ast.Assign, ast.NamedExpr))
                        and isinstance(node.value, ast.Name)
                        and node.value.id in selves
                    ):
                        for alias in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                            if isinstance(alias, ast.Name) and alias.id not in selves:
                                selves.add(alias.id)
                                grew = True
            for node in ast.walk(init):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "__init__"
                    and isinstance(node.func.value, ast.Call)
                    and isinstance(node.func.value.func, ast.Name)
                    and node.func.value.func.id == "super"
                    and not any(
                        isinstance(stmt, ast.Expr) and stmt.value is node for stmt in init.body
                    )
                ):
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            node.lineno,
                            "TB080",
                            f"{where}.__init__ calls super().__init__ inside a branch; a mapper "
                            "calls it as a statement of the constructor body, so the target is "
                            "always initialized",
                        ))
                    )
                targets: list[ast.expr] = []
                if isinstance(node, ast.Assign):
                    targets = list(node.targets)
                elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                    targets = [node.target]
                elif isinstance(node, (ast.For, ast.AsyncFor)):
                    targets = [node.target]
                elif isinstance(node, (ast.With, ast.AsyncWith)):
                    targets = [item.optional_vars for item in node.items if item.optional_vars is not None]
                elif isinstance(node, ast.NamedExpr):
                    targets = [node.target]
                elif isinstance(node, ast.Delete):
                    targets = list(node.targets)
                stored: ast.expr | None = None
                pending = list(targets)
                while pending and stored is None:
                    leaf = pending.pop(0)
                    if isinstance(leaf, (ast.Tuple, ast.List)):
                        pending = list(leaf.elts) + pending
                        continue
                    if isinstance(leaf, ast.Starred):
                        pending.insert(0, leaf.value)
                        continue
                    if not isinstance(leaf, (ast.Attribute, ast.Subscript)):
                        continue
                    root: ast.expr = leaf
                    while isinstance(root, (ast.Attribute, ast.Subscript)):
                        root = root.value
                    if isinstance(root, ast.Name) and root.id in selves:
                        stored = leaf
                if stored is None and (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "__setattr__"
                ):
                    stored = node
                if stored is None and (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in ("setattr", "vars", "delattr")
                    and node.args
                    and isinstance(node.args[0], ast.Name)
                    and node.args[0].id in selves
                ):
                    stored = node
                if stored is None and (
                    isinstance(node, ast.Attribute)
                    and node.attr == "__dict__"
                    and isinstance(node.value, ast.Name)
                    and node.value.id in selves
                ):
                    stored = node
                if stored is None and (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Attribute)
                    and isinstance(node.func.value.value, ast.Name)
                    and node.func.value.value.id in selves
                ):
                    stored = node.func.value
                if stored is not None:
                    named: ast.expr = stored
                    while isinstance(named, ast.Subscript):
                        named = named.value
                    field = (
                        named.attr
                        if isinstance(named, ast.Attribute)
                        else named.func.id
                        if isinstance(named, ast.Call) and isinstance(named.func, ast.Name)
                        else "__setattr__"
                        if isinstance(named, ast.Call)
                        else "__dict__"
                    )
                    found.append(
                        Violation(ViolationSpec(
                            module.path(),
                            stored.lineno,
                            "TB080",
                            f"{where} stores {field!r}; a mapper stores nothing but its target's "
                            "fields — it calls super().__init__ once and assigns nothing itself",
                        ))
                    )
            if supers != 1:
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        init.lineno,
                        "TB080",
                        f"{where}.__init__ calls super().__init__ {supers} times; a mapper "
                        "calls super().__init__ exactly once, because that call is the mapping",
                    ))
                )
        for item in cls.body:
            if isinstance(item, ast.Pass):
                continue
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append(
                    Violation(ViolationSpec(
                        module.path(),
                        item.lineno,
                        "TB080",
                        f"{where} carries a class-level statement; a mapper stores nothing "
                        "but its target's fields, so its body is one __init__",
                    ))
                )
                continue
            if item.name == "__init__":
                continue
            found.append(
                Violation(ViolationSpec(
                    module.path(),
                    item.lineno,
                    "TB080",
                    f"{where}.{item.name} is a method; a mapper holds only __init__, "
                    "because it is its target and the target already carries the fields",
                ))
            )
        return tuple(found)

    @staticmethod
    def _is_enum_auto(module: Module, value: ast.expr) -> bool:
        if not isinstance(value, ast.Call) or value.args or value.keywords:
            return False
        if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name):
            return (
                module._package_aliases.get(value.func.value.id) == ENUM_MODULE
                and value.func.attr == "auto"
            )
        if isinstance(value.func, ast.Name):
            origin = module._imported.get(value.func.id)
            return origin is not None and origin == (ENUM_MODULE, "auto")
        return False

    @staticmethod
    def _returns_outcome(
        module: Module, node: ast.expr, blocks: dict[tuple[str, str], str]
    ) -> bool:
        while isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                node = ast.parse(node.value, mode="eval").body
            except SyntaxError:
                return False
        if not isinstance(node, (ast.Name, ast.Attribute)):
            return False
        key = module._resolve(node)
        return key is not None and blocks.get(key) == OUTCOME_BLOCK

    @staticmethod
    def _form_violations(module: Module, edge: ImportEdge) -> tuple[Violation, ...]:
        target = str(edge._target)
        lineno = int(edge._lineno)
        if str(edge._form) == "bare":
            return (
                Violation(ViolationSpec(
                    module.path(),
                    lineno,
                    "TB053",
                    f"{module.name()} imports {target} without an alias; "
                    "a context module is imported as an aliased module — the analyzer "
                    "resolves a name as attribute over alias",
                )),
            )
        return ()

    def _allowed_annotation(
        self,
        module: Module,
        node: ast.expr | None,
        blocks: dict[tuple[str, str], str],
        allowed_blocks: frozenset[str],
        enums: frozenset[str] = frozenset(),
        primitives: frozenset[str] = PRIMITIVES,
        domain_enums: bool = False,
    ) -> bool:
        if node is None:
            return False
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                try:
                    quoted = ast.parse(node.value, mode="eval").body
                except SyntaxError:
                    return False
                return self._allowed_annotation(module, quoted, blocks, allowed_blocks, enums, primitives, domain_enums)
            return node.value is Ellipsis or node.value is None
        if isinstance(node, ast.Name) and node.id in enums:
            return True
        if isinstance(node, ast.Name) and node.id in primitives:
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left_none = isinstance(node.left, ast.Constant) and node.left.value is None
            right_none = isinstance(node.right, ast.Constant) and node.right.value is None
            if left_none == right_none:
                return False
            wrapped = node.right if left_none else node.left
            return self._allowed_annotation(module, wrapped, blocks, allowed_blocks, enums, primitives, domain_enums)
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name) and node.value.id == "tuple":
                elements = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
                return all(
                    self._allowed_annotation(module, element, blocks, allowed_blocks, enums, primitives, domain_enums)
                    for element in elements
                )
            return False
        key = module._resolve(node)
        if domain_enums and key is not None and key in self._domain_enums:
            return True
        return key is not None and blocks.get(key) in allowed_blocks

