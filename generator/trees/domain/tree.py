from __future__ import annotations

import enum
import re
import typing

import tesser.domain as ts

import tesser.serialization as serialization

READ: typing.Final[str] = "read"

MISSING: typing.Final[str] = "missing"

UNREADABLE: typing.Final[str] = "unreadable"

MALFORMED: typing.Final[str] = "malformed"

OCCUPIED: typing.Final[str] = "occupied"

ENGINE: typing.Final[str] = "restate"

STORE: typing.Final[str] = "postgres"

MINTERS: typing.Final[tuple[str, ...]] = ("domain", "store", "client")

TYPES: typing.Final[dict[str, tuple[str, str, str]]] = {
    "str": ("text", "canonical_str", "__str__"),
    "int": ("bigint", "canonical_int", "__int__"),
}

RESERVED: typing.Final[frozenset[str]] = frozenset(
    {
        "adapters",
        "app",
        "application",
        "client",
        "component",
        "config",
        "conftest",
        "domain",
        "identity",
        "pgdatabase",
        "protocol",
        "spec",
        "srv",
        "tests",
    }
)

SNAKE: typing.Final[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")

OPERATION: typing.Final[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+")

PASCAL: typing.Final[re.Pattern[str]] = re.compile(r"(?:[A-Z][a-z0-9]+)+")

ENVIRONMENT: typing.Final[re.Pattern[str]] = re.compile(r"[A-Z][A-Z0-9_]*")

WORD_START: typing.Final[re.Pattern[str]] = re.compile(r"(?<!^)(?=[A-Z])")

TAG: typing.Final[re.Pattern[str]] = re.compile(r"\{\{([#^/]?)([A-Za-z_][A-Za-z0-9_]*)\}\}")

TEMPLATE_SUFFIX: typing.Final[str] = ".tmpl"


class Health(ts.Outcome):

    CLEAN = enum.auto()
    PROBLEMS = enum.auto()


class Text(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class ScopeSpec(ts.Spec):

    def __init__(
        self,
        values: tuple[tuple[str, str], ...],
        sections: tuple[tuple[str, tuple[tuple[tuple[str, str], ...], ...]], ...],
    ) -> None:
        self.values = values
        self.sections = sections


class Scope(ts.ValueObject):

    _bindings: tuple[
        tuple[tuple[str, str], ...],
        tuple[tuple[str, tuple[tuple[tuple[str, str], ...], ...]], ...],
    ]

    def __init__(self, spec: ScopeSpec) -> None:
        object.__setattr__(self, "_bindings", (spec.values, spec.sections))

    def value(self, name: str) -> Text:
        values, _ = self._bindings
        for key, bound in values:
            if key == name:
                return Text(bound)
        raise ValueError(f"a template names {{{{{name}}}}}, which the spec binds to nothing")

    def enter(self, name: str) -> tuple[Scope, ...]:
        values, sections = self._bindings
        listed = dict(sections)
        if name in listed:
            return tuple(Scope(ScopeSpec(values=item + values, sections=sections)) for item in listed[name])
        for key, bound in values:
            if key == name:
                return (self,) if bound else ()
        raise ValueError(f"a template opens {{{{#{name}}}}}, which the spec binds to nothing")

    def skip(self, name: str) -> tuple[Scope, ...]:
        values, sections = self._bindings
        listed = dict(sections)
        if name in listed:
            return () if listed[name] else (self,)
        for key, bound in values:
            if key == name:
                return () if bound else (self,)
        raise ValueError(f"a template opens {{{{^{name}}}}}, which the spec binds to nothing")


class Template(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)

    def render(self, scope: Scope) -> Text:
        text = self._value
        rendered: list[str] = []
        position = 0
        tag = TAG.search(text, position)
        while tag is not None:
            sigil = tag.group(1)
            name = tag.group(2)
            if sigil == "":
                rendered.append(text[position : tag.start()])
                rendered.append(str(scope.value(name)))
                position = tag.end()
                tag = TAG.search(text, position)
                continue
            if sigil == "/":
                raise ValueError(f"a template closes {{{{/{name}}}}} before it opens it")
            depth = 1
            close = TAG.search(text, tag.end())
            while close is not None:
                if close.group(2) == name and close.group(1) in ("#", "^"):
                    depth += 1
                elif close.group(2) == name and close.group(1) == "/":
                    depth -= 1
                    if depth == 0:
                        break
                close = TAG.search(text, close.end())
            if close is None:
                raise ValueError(f"a template never closes {{{{{sigil}{name}}}}}")
            open_start = text.rfind("\n", 0, tag.start()) + 1
            open_stop = text.find("\n", tag.end())
            open_stop = len(text) if open_stop == -1 else open_stop
            open_alone = (
                open_start >= position
                and not text[open_start : tag.start()].strip()
                and not text[tag.end() : open_stop].strip()
            )
            close_start = text.rfind("\n", 0, close.start()) + 1
            close_stop = text.find("\n", close.end())
            close_stop = len(text) if close_stop == -1 else close_stop
            close_alone = (
                close_start >= tag.end()
                and not text[close_start : close.start()].strip()
                and not text[close.end() : close_stop].strip()
            )
            rendered.append(text[position:open_start] if open_alone else text[position : tag.start()])
            inner_start = open_stop + 1 if open_alone else tag.end()
            inner_stop = close_start if close_alone else close.start()
            inner = text[inner_start:inner_stop] if inner_start < inner_stop else ""
            entered = scope.enter(name) if sigil == "#" else scope.skip(name)
            rendered.extend(str(Template(inner).render(each)) for each in entered)
            position = close_stop + 1 if close_alone else close.end()
            tag = TAG.search(text, position)
        rendered.append(text[position:])
        return Text("".join(rendered))


class GeneratedFileSpec(ts.Spec):

    def __init__(self, path: str, content: str) -> None:
        self.path = path
        self.content = content


class GeneratedFile(ts.ValueObject):

    _path: Text
    _content: Text

    def __init__(self, spec: GeneratedFileSpec) -> None:
        object.__setattr__(self, "_path", Text(spec.path))
        object.__setattr__(self, "_content", Text(spec.content))

    def path(self) -> Text:
        return self._path

    def content(self) -> Text:
        return self._content


class GenerationPathsSpec(ts.Spec):

    def __init__(self, spec_path: str, out_dir: str) -> None:
        self.spec_path = spec_path
        self.out_dir = out_dir


class GenerationPaths(ts.ValueObject):

    _spec_path: Text
    _out_dir: Text

    def __init__(self, spec: GenerationPathsSpec) -> None:
        object.__setattr__(self, "_spec_path", Text(spec.spec_path))
        object.__setattr__(self, "_out_dir", Text(spec.out_dir))

    def spec_path(self) -> Text:
        return self._spec_path

    def out_dir(self) -> Text:
        return self._out_dir


class TreeSpec(ts.Spec):

    def __init__(
        self,
        state: str,
        note: str,
        target: str,
        app: str,
        context: str,
        aggregate: str,
        engine: str,
        store: str,
        identity: str,
        minted_by: str,
        fields: tuple[tuple[str, str], ...],
        write: str,
        read: str,
        read_answers: tuple[str, ...],
        orchestrator: str,
        action: str,
        save: str,
        load: str,
        asserts: str,
        storage_env: str,
        ingress_env: str,
        templates: tuple[tuple[str, str], ...],
    ) -> None:
        self.state = state
        self.note = note
        self.target = target
        self.app = app
        self.context = context
        self.aggregate = aggregate
        self.engine = engine
        self.store = store
        self.identity = identity
        self.minted_by = minted_by
        self.fields = fields
        self.write = write
        self.read = read
        self.read_answers = read_answers
        self.orchestrator = orchestrator
        self.action = action
        self.save = save
        self.load = load
        self.asserts = asserts
        self.storage_env = storage_env
        self.ingress_env = ingress_env
        self.templates = templates


class Tree(ts.AggregateRoot):

    def __init__(self, spec: TreeSpec) -> None:
        found: list[Text] = []
        if spec.state == MISSING:
            found.append(Text(f"there is no spec file at {spec.note}"))
        elif spec.state == UNREADABLE:
            found.append(Text(f"the spec file at {spec.note} is not readable UTF-8 text"))
        elif spec.state == MALFORMED:
            found.append(Text(f"the spec file is not TOML: {spec.note}"))
        elif spec.state != READ:
            found.append(Text(f"the spec file could not be read: {spec.state}"))
        else:
            shaped = (
                ("app", spec.app, SNAKE, "a snake_case name, like voice"),
                ("context", spec.context, SNAKE, "a snake_case name, like calls"),
                ("aggregate", spec.aggregate, PASCAL, "a PascalCase name, like Call"),
                ("identity name", spec.identity, SNAKE, "a snake_case name, like call_id"),
                ("client write", spec.write, OPERATION, "a snake_case verb and noun, like place_call"),
                ("client read", spec.read, OPERATION, "a snake_case verb and noun, like get_call"),
                ("orchestrator operation", spec.orchestrator, OPERATION, "a snake_case verb and noun, like conduct_call"),
                ("action operation", spec.action, OPERATION, "a snake_case verb and noun, like record_call"),
                ("port save", spec.save, OPERATION, "a snake_case verb and noun, like save_call"),
                ("port load", spec.load, OPERATION, "a snake_case verb and noun, like load_call"),
                ("acceptance asserts", spec.asserts, SNAKE, "a field name"),
                ("env storage", spec.storage_env, ENVIRONMENT, "an upper-case environment variable name"),
                ("env ingress", spec.ingress_env, ENVIRONMENT, "an upper-case environment variable name"),
            )
            for key, value, shape, described in shaped:
                if not value:
                    found.append(Text(f"the spec names no {key}"))
                elif shape.fullmatch(value) is None:
                    found.append(Text(f"{key} '{value}' is not {described}"))
            if spec.engine != ENGINE:
                found.append(Text(f"engine '{spec.engine}' has no templates; the one engine is '{ENGINE}'"))
            if spec.store != STORE:
                found.append(Text(f"store '{spec.store}' has no templates; the one store is '{STORE}'"))
            if spec.minted_by not in MINTERS:
                found.append(
                    Text(f"identity minted_by '{spec.minted_by}' is not one of {', '.join(MINTERS)}")
                )
            if spec.context in RESERVED:
                found.append(Text(f"context '{spec.context}' is a name the generated tree already uses"))
            if not spec.fields:
                found.append(Text("the spec names no fields"))
            identity_class = "".join(part.capitalize() for part in spec.identity.split("_"))
            taken = {spec.aggregate, identity_class, f"{spec.aggregate}Spec"}
            field_names = tuple(name for name, _ in spec.fields)
            for name, kind in spec.fields:
                if SNAKE.fullmatch(name) is None:
                    found.append(Text(f"field '{name}' is not a snake_case name"))
                if name == spec.identity:
                    found.append(Text(f"field '{name}' is the identity, which every record already carries"))
                if name in RESERVED:
                    found.append(Text(f"field '{name}' is a name the generated tree already uses"))
                if kind not in TYPES:
                    found.append(Text(f"field '{name}' is a '{kind}'; a field is one of {', '.join(TYPES)}"))
                if "".join(part.capitalize() for part in name.split("_")) in taken:
                    found.append(Text(f"field '{name}' names a class the domain module already declares"))
            answers = tuple(answer for answer in spec.read_answers if answer != spec.identity)
            for answer in answers:
                if answer not in field_names:
                    found.append(Text(f"client read answers '{answer}', which is not a field"))
            if spec.asserts and spec.asserts not in answers:
                found.append(Text(f"acceptance asserts '{spec.asserts}', which the client read does not answer"))
            issue = f"issue_{spec.identity}"
            operations = [spec.write, spec.read, spec.orchestrator, spec.action, spec.save, spec.load]
            if spec.minted_by == "store":
                operations.append(issue)
            for operation in sorted({operation for operation in operations if operations.count(operation) > 1}):
                found.append(Text(f"operation '{operation}' is named twice; every operation has a name of its own"))
            if spec.target == OCCUPIED:
                found.append(Text("the output directory is not empty"))
            if not spec.templates:
                found.append(Text("no templates were found"))
        self._problems = tuple(found)
        if found:
            self._files: tuple[GeneratedFile, ...] = ()
            return
        classes = {
            name: "".join(part.capitalize() for part in name.split("_"))
            for name in (
                spec.app,
                spec.context,
                spec.identity,
                spec.write,
                spec.read,
                spec.orchestrator,
                spec.action,
                spec.save,
                spec.load,
                issue,
                *field_names,
            )
        }
        typed = dict(spec.fields)
        items: dict[str, tuple[tuple[str, str], ...]] = {}
        for name in (spec.identity, *field_names):
            kind = typed.get(name, "str")
            sql_type, canonical, dunder = TYPES[kind]
            quoted = kind == "str"
            items[name] = (
                ("field", name),
                ("Field", classes[name]),
                ("py_type", kind),
                ("sql_type", sql_type),
                ("canonical", canonical),
                ("dunder", dunder),
                ("sample", f'"{name}-1"' if quoted else "1"),
                ("sample2", f'"{name}-2"' if quoted else "2"),
                ("wrong", "1" if quoted else '"1"'),
                ("fresh", "str(uuid.uuid4())" if name == spec.identity else (f'"{name}-1"' if quoted else "1")),
                ("accessor", "identity" if name == spec.identity else name),
                ("is_identity", "true" if name == spec.identity else ""),
            )
        record_names = (spec.identity, *field_names)
        listed = (
            ("fields", field_names),
            ("record_fields", record_names),
            ("read_fields", (spec.identity, *answers)),
            ("write_fields", record_names if spec.minted_by == "client" else field_names),
            ("spec_fields", field_names if spec.minted_by == "domain" else record_names),
        )
        sections = tuple(
            (
                section,
                tuple(
                    items[name]
                    + (
                        ("comma", ", " if index < len(names) - 1 else ""),
                        (
                            "prose",
                            ""
                            if index == 0
                            else (" and " if len(names) == 2 else (", and " if index == len(names) - 1 else ", ")),
                        ),
                        ("position", str(index + 1)),
                    )
                    for index, name in enumerate(names)
                ),
            )
            for section, names in listed
        )
        asserted = typed.get(spec.asserts, "str")
        values = (
            ("app", spec.app),
            ("App", classes[spec.app]),
            ("context", spec.context),
            ("Context", classes[spec.context]),
            ("aggregate", WORD_START.sub("_", spec.aggregate).lower()),
            ("Aggregate", spec.aggregate),
            ("identity", spec.identity),
            ("Identity", classes[spec.identity]),
            ("identity_sample", f'"{spec.identity}-1"'),
            ("identity_sample2", f'"{spec.identity}-2"'),
            ("identity_raw", f"{spec.identity}-1"),
            ("write", spec.write),
            ("Write", classes[spec.write]),
            ("read", spec.read),
            ("Read", classes[spec.read]),
            ("conduct", spec.orchestrator),
            ("Conduct", classes[spec.orchestrator]),
            ("conduct_words", spec.orchestrator.replace("_", " ")),
            ("record", spec.action),
            ("Record", classes[spec.action]),
            ("record_words", spec.action.replace("_", " ")),
            ("save", spec.save),
            ("Save", classes[spec.save]),
            ("load", spec.load),
            ("Load", classes[spec.load]),
            ("issue", issue),
            ("Issue", classes[issue]),
            ("storage_env", spec.storage_env),
            ("ingress_env", spec.ingress_env),
            ("asserts", spec.asserts),
            (
                "asserts_choices",
                f'("{spec.asserts}-a", "{spec.asserts}-b", "{spec.asserts}-c", "{spec.asserts}-d")'
                if asserted == "str"
                else "(11, 12, 13, 14)",
            ),
            ("domain_mints", "true" if spec.minted_by == "domain" else ""),
            ("store_mints", "true" if spec.minted_by == "store" else ""),
            ("client_mints", "true" if spec.minted_by == "client" else ""),
        )
        scope = Scope(ScopeSpec(values=values, sections=sections))
        self._files = tuple(
            sorted(
                (
                    GeneratedFile(
                        GeneratedFileSpec(
                            path=str(Template(path).render(scope)).removesuffix(TEMPLATE_SUFFIX),
                            content=str(Template(text).render(scope)),
                        )
                    )
                    for path, text in spec.templates
                ),
                key=str,
            )
        )

    def health(self) -> Health:
        return Health.PROBLEMS if self._problems else Health.CLEAN

    def problems(self) -> tuple[Text, ...]:
        return self._problems

    def files(self) -> tuple[GeneratedFile, ...]:
        return self._files
