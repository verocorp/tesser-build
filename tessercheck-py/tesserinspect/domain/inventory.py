from __future__ import annotations

import ast
import typing

import tesser.domain as ts
import tesser.errors as errors
import tesser.serialization as serialization

READERS: typing.Final[frozenset[str]] = frozenset(
    {
        "read_text",
        "read_bytes",
        "open",
        "getsource",
        "getsourcelines",
        "getfile",
        "getsourcefile",
        "parse",
        "glob",
        "rglob",
        "iterdir",
        "walk",
    }
)
CONFIGS: typing.Final[frozenset[str]] = frozenset(
    {
        "conftest.py",
        "pytest.ini",
        ".pytest.ini",
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
    }
)


class EvidenceText(ts.ValueObject):
    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class CheckoutLocation(ts.ValueObject):
    _value: str

    def __init__(self, value: str) -> None:
        if not value or "\x00" in value:
            raise errors.invalid("invalid_repo", "repo must name a checkout directory")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class BaselineReference(ts.ValueObject):
    _value: str

    def __init__(self, value: str) -> None:
        if not value or value.startswith("-") or "\x00" in value:
            raise errors.invalid(
                "invalid_base", "base must be a commit/ref, not an option"
            )
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class EvidenceLine(ts.ValueObject):
    _value: int

    def __init__(self, value: int) -> None:
        if value < 0:
            raise errors.invalid("invalid_line", "evidence line must be nonnegative")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return serialization.canonical_int(self._value)


class CandidateSpec(ts.Spec):
    def __init__(
        self, kind: str, path: str, line: int, symbol: str, reason: str
    ) -> None:
        self.kind = kind
        self.path = path
        self.line = line
        self.symbol = symbol
        self.reason = reason


class Candidate(ts.ValueObject):
    _kind: EvidenceText
    _path: EvidenceText
    _line: EvidenceLine
    _symbol: EvidenceText
    _reason: EvidenceText

    def __init__(self, spec: CandidateSpec) -> None:
        object.__setattr__(self, "_kind", EvidenceText(spec.kind))
        object.__setattr__(self, "_path", EvidenceText(spec.path))
        object.__setattr__(self, "_line", EvidenceLine(spec.line))
        object.__setattr__(self, "_symbol", EvidenceText(spec.symbol))
        object.__setattr__(self, "_reason", EvidenceText(spec.reason))

    def kind(self) -> EvidenceText:
        return self._kind

    def path(self) -> EvidenceText:
        return self._path

    def line(self) -> EvidenceLine:
        return self._line

    def symbol(self) -> EvidenceText:
        return self._symbol

    def reason(self) -> EvidenceText:
        return self._reason


class InventorySpec(ts.Spec):
    def __init__(
        self,
        sources: tuple[tuple[str, str], ...],
        changes: tuple[tuple[str, str, str], ...],
        paths: tuple[str, ...],
    ) -> None:
        self.sources = sources
        self.changes = changes
        self.paths = paths


class Inventory(ts.ValueObject):
    _candidates: tuple[Candidate, ...]
    _changed_tests: tuple[EvidenceText, ...]

    def __init__(self, spec: InventorySpec) -> None:
        changed = set()
        for path, previous, status in spec.changes:
            for name in (path, previous):
                leaf = name.rsplit("/", 1)[-1]
                if leaf.endswith(".py") and (
                    leaf.startswith("test_")
                    or leaf.endswith("_test.py")
                    or leaf == "conftest.py"
                ):
                    changed.add(name)
        rows: set[tuple[str, str, int, str, str]] = set()
        modules = {}
        for path, text in spec.sources:
            try:
                modules[path] = ast.parse(text, filename=path)
            except (SyntaxError, ValueError) as error:
                raise errors.invalid(
                    "python_parse_error", f"{path}: {error}"
                ) from error
        for path in sorted(changed):
            rows.add(
                (
                    "changed-test",
                    path,
                    0,
                    "",
                    "Changed test source; inspect collection, helpers and fixtures before choosing checks.",
                )
            )
        for path, tree in sorted(modules.items()):
            aliases = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        aliases[alias.asname or alias.name] = alias.name
                        if path in changed:
                            rows.add(
                                (
                                    "import-reference",
                                    path,
                                    node.lineno,
                                    alias.asname or alias.name,
                                    f"Imported {'.' * node.level}{node.module or ''}.{alias.name}; inspect the defining module and any helper contract.",
                                )
                            )
                elif isinstance(node, ast.Import) and path in changed:
                    for alias in node.names:
                        rows.add(
                            (
                                "import-reference",
                                path,
                                node.lineno,
                                alias.asname or alias.name,
                                f"Imported {alias.name}; inspect helper and fixture definitions reached through this alias.",
                            )
                        )
            definitions = [
                (node.name, node)
                for node in tree.body
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                )
            ]
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    definitions.extend(
                        (f"{node.name}.{child.name}", child)
                        for child in node.body
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
            for symbol, node in definitions:
                operations = set()
                references = set()
                for child in ast.walk(node):
                    if isinstance(child, ast.Name):
                        references.add(aliases.get(child.id, child.id))
                    elif isinstance(child, ast.Attribute):
                        references.add(child.attr)
                    elif isinstance(child, ast.arg):
                        references.add(child.arg)
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            operations.add(aliases.get(child.func.id, child.func.id))
                        elif isinstance(child.func, ast.Attribute):
                            operations.add(child.func.attr)
                if changed and operations & READERS:
                    rows.add(
                        (
                            "source-reader",
                            path,
                            node.lineno,
                            symbol,
                            "Source/file inspection operations: "
                            + ", ".join(sorted(operations & READERS))
                            + "; may constrain changed test text without calling it.",
                        )
                    )
                if path in changed:
                    for helper, definition in definitions:
                        if helper.rsplit(".", 1)[
                            -1
                        ] in references and not helper.rsplit(".", 1)[-1].startswith(
                            ("test_", "Test")
                        ):
                            rows.add(
                                (
                                    "helper",
                                    path,
                                    definition.lineno,
                                    helper,
                                    f"Referenced by {symbol}; inspect the helper's own construction contract.",
                                )
                            )
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for argument in (
                            node.args.posonlyargs
                            + node.args.args
                            + node.args.kwonlyargs
                        ):
                            if argument.arg not in {"self", "cls"} and (
                                node.name.startswith("test_") or node.decorator_list
                            ):
                                rows.add(
                                    (
                                        "fixture-reference",
                                        path,
                                        node.lineno,
                                        argument.arg,
                                        f"Parameter of {symbol}; may be an injected fixture or parametrization.",
                                    )
                                )
            if changed:
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    for decorator in node.decorator_list:
                        target = (
                            decorator.func
                            if isinstance(decorator, ast.Call)
                            else decorator
                        )
                        name = (
                            aliases.get(target.id, target.id)
                            if isinstance(target, ast.Name)
                            else target.attr
                            if isinstance(target, ast.Attribute)
                            else ""
                        )
                        if name == "fixture":
                            rows.add(
                                (
                                    "fixture-definition",
                                    path,
                                    node.lineno,
                                    node.name,
                                    "Declared fixture; review scope, autouse, dependencies and any name override.",
                                )
                            )
        for path in set(spec.paths) | {
            name
            for path, previous, status in spec.changes
            for name in (path, previous)
            if name
        }:
            parent = path.rpartition("/")[0]
            if path.rsplit("/", 1)[-1] in CONFIGS and any(
                not parent or test.startswith(parent + "/") for test in changed
            ):
                rows.add(
                    (
                        "collection",
                        path,
                        0,
                        "",
                        "Ancestor collection configuration can affect fixtures, imports and plugins.",
                    )
                )
        object.__setattr__(
            self,
            "_candidates",
            tuple(Candidate(CandidateSpec(*row)) for row in sorted(rows)),
        )
        object.__setattr__(
            self,
            "_changed_tests",
            tuple(EvidenceText(path) for path in sorted(changed)),
        )

    def candidates(self) -> tuple[Candidate, ...]:
        return self._candidates

    def changed_tests(self) -> tuple[EvidenceText, ...]:
        return self._changed_tests
